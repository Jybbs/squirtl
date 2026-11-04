"""
Defines `Replay`, the replay memory the agent stores each transition in and
samples each batch from, `Batch`, the transitions one update draws from it,
and `Column`, one entry's elements across its slots.
"""

from collections.abc  import Mapping
from gymnasium.spaces import Box, Dict, MultiBinary
from numpy            import arange, asarray, flatnonzero, float32, int64, ndarray, packbits, uint8, unpackbits, zeros
from numpy.random     import Generator
from operator         import itemgetter
from pydantic         import InstanceOf
from torch            import Tensor, as_tensor, no_grad

from squirtl.agent.networks   import QNetwork
from squirtl.emulator.schemas import Record


class Batch(Record):
    """
    The transitions one update draws from replay memory, each field on the
    device the settings name.
    """

    actions: InstanceOf[Tensor]
    """
    The action each draw took, a `(batch,)` tensor of `int64`.
    """

    rewards: InstanceOf[Tensor]
    """
    The reward each draw earned, a `(batch,)` tensor of `float32`.
    """

    terminated: InstanceOf[Tensor]
    """
    Whether each draw ended its episode, a `(batch,)` tensor of `bool`.
    """

    windows: dict[str, InstanceOf[Tensor]]
    """
    One `(batch, depth + 1, *element)` tensor per entry, its first `depth`
    elements the observation acted on and its last `depth` the one reached.
    """

    @property
    def next_observations(self) -> dict[str, Tensor]:
        """
        Slices the observation each draw reached out of `windows`.
        """
        return {key: window[:, 1:] for key, window in self.windows.items()}

    @property
    def observations(self) -> dict[str, Tensor]:
        """
        Slices the observation each draw acted on out of `windows`.
        """
        return {key: window[:, :-1] for key, window in self.windows.items()}

    @no_grad()
    def targets(self, chooser: QNetwork, discount: float, network: QNetwork) -> Tensor:
        """
        Values each draw at its reward plus `discount` times the value
        `network` gives the observation reached under the action `chooser`
        values highest there, or the reward alone where it terminated,
        recording no autograd graph. Where `chooser` is the online network
        and `network` the target network, the target is van Hasselt et al.'s
        Double DQN target, and where both are the target network, it is the
        highest value the target network gives, as Mnih et al.'s is, read
        from one pass of `network`.
        """
        reached = self.next_observations
        valued  = network(reached)
        chosen  = valued if chooser is network else chooser(reached)

        return (
            self.rewards
            + discount
                * valued.gather(1, chosen.argmax(1, keepdim=True))[:, 0]
                * ~self.terminated
        )

    def values(self, network: QNetwork) -> Tensor:
        """
        Reads the value `network` gives each draw's action on the
        observation it acted on.
        """
        return network(self.observations).gather(1, self.actions[:, None])[:, 0]


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
        Takes each array of `arrays` in place of the one `self.arrays` holds
        under its name, uncopied, then reads `pushed` back from the array of
        no dimensions holding it, once every name, shape, and dtype matches.

        Raises:
            ValueError: Where `arrays` names other arrays than replay memory
                        holds, or one differs in shape or dtype from the one
                        it replaces, before any is taken.
        """
        held = self.arrays

        if arrays.keys() != held.keys():
            raise ValueError(
                f"replay memory holds {sorted(held)}, where the arrays loaded are "
                f"{sorted(arrays)}"
            )

        for name, array in held.items():
            if (arrays[name].dtype, arrays[name].shape) != (array.dtype, array.shape):
                raise ValueError(
                    f"replay memory holds `{name}` as {array.dtype} at the shape "
                    f"{array.shape}, where the arrays loaded hold "
                    f"{arrays[name].dtype} at {arrays[name].shape}"
                )

        self.actions, self.held, self.rewards, self.terminated = itemgetter(
            "actions",
            "held",
            "rewards",
            "terminated"
        )(arrays)
        self.pushed = arrays["pushed"].item()

        for key, column in self.columns.items():
            column.elements = arrays[key]

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
