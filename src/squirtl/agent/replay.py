"""
Defines the replay memory the agent stores each transition in and draws each
update's batch from:

- `Column`, the elements one entry of an observation holds across the slots
- `Replay`, the replay memory itself
"""

from collections.abc  import Mapping
from gymnasium.spaces import Box, Dict, MultiBinary
from numpy            import arange, count_nonzero, flatnonzero, float32, int64, ndarray, packbits, uint8, unpackbits
from numpy            import zeros
from numpy.random     import Generator
from torch            import as_tensor

from squirtl.agent.schemas import Batch


class Column:
    """
    The elements one entry of a `Dict` observation holds in replay memory,
    one per slot, each element of a `MultiBinary` entry packed eight cells
    to a byte along its last axis.
    """

    def __init__(self, capacity: int, space: Box | MultiBinary):
        """
        Allocates `capacity` slots for the elements `space` stacks along
        its first axis, `depth` holding how many one observation stacks
        and `width` the length of an element's last axis before packing, or
        `None` where the column holds each element as it is.
        """
        self.depth, *element = space.shape

        if isinstance(space, MultiBinary):
            self.elements = zeros(
                (capacity, *packbits(zeros(element, uint8), axis=-1).shape),
                uint8
            )
            self.width = element[-1]
        else:
            self.elements = zeros((capacity, *element), space.dtype)
            self.width    = None

    def window(self, slots: ndarray) -> ndarray:
        """
        Takes the `depth` elements ending at each of `slots` and the one
        after it, wrapping past the last slot, unpacked where they are
        packed.

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
        Writes `element` into `slot`, packed where the column packs.
        """
        self.elements[slot] = element if self.width is None else packbits(
            element,
            axis = -1
        )


class Replay:
    """
    Replay memory over one `Column` per entry of a `Dict` observation,
    beside the action taken on the observation each slot ends, its reward,
    and whether it terminated the episode.

    A reset observation is stored whole, each entry's stack ending at one
    slot, and each later step stores the newest element of each entry,
    so the stacks ending at a slot are the observation acted on and those
    ending one slot later the one reached. A slot holds a transition only
    while both lie in one episode and neither has been overwritten.
    """

    def __init__(self, capacity: int, generator: Generator, space: Dict):
        """
        Allocates `capacity` slots of each entry `space` declares, drawing
        every batch from `generator`.
        """
        self.actions    = zeros(capacity, int64)
        self.columns    = {key: Column(capacity, entry) for key, entry in space.items()}
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
        Draws `size` transitions uniformly with replacement from those held
        and moves them onto `device` as one batch.
        """
        slots = self.generator.choice(flatnonzero(self.held), size)

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
        slot, with its `reward` and whether it `terminated` the episode,
        then stores the newest element of each entry of the `observation`
        reached.
        """
        slot = (self.pushed - 1) % len(self.held)

        self.actions[slot]    = action
        self.held[slot]       = True
        self.rewards[slot]    = reward
        self.terminated[slot] = terminated
        self.push({key: stack[-1] for key, stack in observation.items()})
