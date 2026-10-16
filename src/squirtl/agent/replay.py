"""
Defines `Replay`, the replay memory the agent stores each transition in
and samples each batch from, and `Column`, one entry's elements across its
slots.
"""

from collections.abc  import Mapping
from gymnasium.spaces import Box, Dict, MultiBinary
from numpy            import arange, asarray, copyto, count_nonzero, flatnonzero, float32, int64, ndarray, packbits
from numpy            import uint8, unpackbits, zeros
from numpy.random     import Generator
from torch            import as_tensor

from squirtl.agent.schemas import Batch


class Column:
    """
    One entry's elements in replay memory, one per slot, each element of a
    `MultiBinary` entry packed eight cells to a byte along its last axis.
    """

    def __init__(self, capacity: int, space: Box | MultiBinary):
        """
        Allocates `capacity` slots for the elements `space` stacks, with
        `depth` the number one observation stacks and `width` the last
        axis's length before packing, or `None` where nothing packs.
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
        after, wrapping past the last slot and unpacking packed elements.

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
    beside each slot's action, reward, and termination.

    A reset observation is stored whole and each later step stores
    each entry's newest element, so the stacks ending at a slot are the
    observation acted on and those one slot later the one reached. A
    slot holds a transition while both lie in one episode and neither is
    overwritten.
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
    def arrays(self) -> dict[str, ndarray]:
        """
        Gathers each array replay memory holds, uncopied, under its name,
        each column's elements under the key of its entry, beside `pushed`
        as an array of no dimensions.
        """
        return {
            "actions"    : self.actions,
            "held"       : self.held,
            "pushed"     : asarray(self.pushed),
            "rewards"    : self.rewards,
            "terminated" : self.terminated,
            **{key: column.elements for key, column in self.columns.items()}
        }

    @property
    def depth(self) -> int:
        """
        Reads the deepest entry's depth, the most slots one observation
        reads.
        """
        return max(column.depth for column in self.columns.values())

    def begin(self, observation: Mapping[str, ndarray]):
        """
        Stores each element of a reset observation, every stack ending at
        the newest slot and a shallower entry repeating its oldest element
        before its stack.
        """
        for index in range(-self.depth, 0):
            self.push(
                {
                    key: stack[max(index, -len(stack))]
                    for key, stack in observation.items()
                }
            )

    def load(self, arrays: Mapping[str, ndarray]):
        """
        Copies each array of `arrays` into the one `self.arrays` holds under
        its name, then reads `pushed` back from the array of no dimensions
        holding it.

        Raises:
            ValueError: Where an array's shape does not broadcast to the
                        shape of the one it replaces.
        """
        for name, array in self.arrays.items():
            copyto(array, arrays[name])

        self.pushed = arrays["pushed"].item()

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
        slot, with its `reward` and `terminated`, then stores each entry's
        newest element of the `observation` reached.
        """
        slot = (self.pushed - 1) % len(self.held)

        self.actions[slot]    = action
        self.held[slot]       = True
        self.rewards[slot]    = reward
        self.terminated[slot] = terminated
        self.push({key: stack[-1] for key, stack in observation.items()})
