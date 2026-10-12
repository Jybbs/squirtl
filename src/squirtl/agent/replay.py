"""
Defines the replay memory the agent stores each transition in and draws each
update's batch from:

- `Column`, the elements one entry of an observation holds across the slots
- `Replay`, the replay memory itself
"""

from collections.abc  import Mapping
from dataclasses      import dataclass
from gymnasium.spaces import Box, Dict
from numpy            import arange, count_nonzero, float32, int64, ndarray, packbits, uint8, unpackbits, zeros
from numpy.random     import Generator
from torch            import as_tensor
from typing           import Self

from squirtl.agent.schemas import Batch


@dataclass(frozen=True, kw_only=True)
class Column:
    """
    The elements one entry of a `Dict` observation holds in replay memory,
    one per slot, where a binary entry holds each element packed eight cells
    to a byte along its last axis through `packbits`.
    """

    depth: int
    """
    The elements one observation of the entry stacks along its first axis.
    """

    elements: ndarray
    """
    The element each slot holds, packed along its last axis where `width`
    is set.
    """

    width: int | None
    """
    The length of each element's last axis before packing, or `None` where
    the column holds its elements as they are.
    """

    @classmethod
    def allocate(cls, capacity: int, space: Box) -> Self:
        """
        Allocates `capacity` slots for the elements `space` stacks along its
        first axis, packing them where `space` holds `uint8` cells bounded
        at 0 and 1, since `unpackbits` returns `uint8`.
        """
        depth, *element = space.shape

        if space.dtype == uint8 and (space.low == 0).all() and (space.high == 1).all():
            return cls(
                depth    = depth,
                elements = zeros(
                    (capacity, *packbits(zeros(element, uint8), axis=-1).shape),
                    uint8
                ),
                width = element[-1]
            )

        return cls(
            depth    = depth,
            elements = zeros((capacity, *element), space.dtype),
            width    = None
        )

    def window(self, slots: ndarray) -> ndarray:
        """
        Takes the `depth` elements ending at each of `slots` and the one
        after it, wrapping past the last slot, and unpacks them where the
        column packs its elements.

        Returns:
            A `(len(slots), depth + 1, *element)` array.
        """
        window = self.elements.take(
            slots[:, None] + arange(1 - self.depth, 2),
            axis = 0,
            mode = "wrap"
        )

        return window if self.width is None else unpackbits(
            window,
            axis  = -1,
            count = self.width
        )

    def write(self, element: ndarray, slot: int):
        """
        Writes `element` into `slot`, packing it where the column packs
        its elements.
        """
        self.elements[slot] = element if self.width is None else packbits(
            element,
            axis = -1
        )


class Replay:
    """
    Replay memory over one `Column` for each entry of a `Dict` observation,
    beside the action taken on the observation each slot ends, the reward it
    earned, and whether it terminated the episode.

    An episode's reset observation is stored whole, every entry's stack
    ending at the same slot, and every step after it stores only the
    newest element of each entry, so the stacks ending at a slot are the
    observation the policy acted on and those ending one slot later are
    the one the action reached. A slot holds a transition only where both
    observations lie within one episode and no element of either has been
    overwritten since.
    """

    def __init__(self, capacity: int, generator: Generator, space: Dict):
        """
        Allocates room for `capacity` slots of each entry `space` declares,
        each entry stacked along its first axis, drawing every batch from
        `generator`.
        """
        self.actions = zeros(capacity, int64)
        self.columns = {
            key: Column.allocate(capacity, subspace) for key, subspace in space.items()
        }
        self.generator  = generator
        self.held       = zeros(capacity, bool)
        self.pushed     = 0
        self.rewards    = zeros(capacity, float32)
        self.terminated = zeros(capacity, bool)

    def __len__(self) -> int:
        """
        Counts the transitions replay memory holds.
        """
        return count_nonzero(self.held)

    @property
    def depth(self) -> int:
        """
        Reads the depth of the deepest entry's stack, the most slots one
        observation reads.
        """
        return max(column.depth for column in self.columns.values())

    def begin(self, observation: Mapping[str, ndarray]):
        """
        Stores every element of an episode's reset observation, each entry's
        stack ending at the newest slot and an entry shallower than `depth`
        repeating its oldest element over the slots before its stack.
        """
        for index in range(-self.depth, 0):
            self.push(
                {
                    key: stack[max(index, -len(stack))]
                    for key, stack in observation.items()
                }
            )

    def push(self, elements: Mapping[str, ndarray]):
        """
        Writes one element of each entry into the oldest slot, releasing
        each transition whose observations read that slot.
        """
        self.held.put(self.pushed + arange(self.depth), False, mode="wrap")

        for key, element in elements.items():
            self.columns[key].write(element, self.pushed % len(self.held))

        self.pushed += 1

    def sample(self, device: str, size: int) -> Batch:
        """
        Draws `size` transitions uniformly with replacement from those held,
        redrawing each draw landing on a slot that holds none, and moves
        them onto `device` as one batch.
        """
        filled = min(self.pushed, len(self.held))
        slots  = self.generator.integers(filled, size=size)

        while (missed := ~self.held[slots]).any():
            slots[missed] = self.generator.integers(filled, size=count_nonzero(missed))

        return Batch(
            actions    = as_tensor(self.actions[slots], device=device),
            rewards    = as_tensor(self.rewards[slots], device=device),
            terminated = as_tensor(self.terminated[slots], device=device),
            windows    = {
                key: as_tensor(column.window(slots), device=device)
                for key, column in self.columns.items()
            }
        )

    def store(
        self,
        action      : int,
        observation : Mapping[str, ndarray],
        reward      : float,
        terminated  : bool
    ):
        """
        Records `action`, taken on the observation ending at the newest
        slot, with the `reward` it earned and whether it `terminated`
        the episode, then stores the newest element of each entry of the
        `observation` it reached.
        """
        slot = (self.pushed - 1) % len(self.held)

        self.actions[slot]    = action
        self.held[slot]       = True
        self.rewards[slot]    = reward
        self.terminated[slot] = terminated
        self.push({key: stack[-1] for key, stack in observation.items()})
