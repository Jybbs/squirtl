"""
Defines `Replay`, the replay memory the agent stores each transition in and
draws each update's batch from.
"""

from collections.abc  import Mapping
from gymnasium.spaces import Dict
from numpy            import arange, count_nonzero, float32, int64, ndarray, zeros
from numpy.random     import Generator
from torch            import as_tensor

from squirtl.agent.schemas import Batch


class Replay:
    """
    Replay memory over arrays holding, for each entry of a `Dict`
    observation, one element of that entry's stack per slot, beside the
    action taken on the observation that slot ends, the reward it earned,
    and whether it terminated the episode.

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
        self.actions      = zeros(capacity, int64)
        self.depths       = {key: subspace.shape[0] for key, subspace in space.items()}
        self.generator    = generator
        self.held         = zeros(capacity, bool)
        self.observations = {
            key: zeros((capacity, *subspace.shape[1:]), subspace.dtype)
            for key, subspace in space.items()
        }
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
        return max(self.depths.values())

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
            self.observations[key][self.pushed % len(self.held)] = element

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
                key: as_tensor(
                    array.take(
                        # The `depth` elements ending at each slot and the one after.
                        slots[:, None] + arange(1 - self.depths[key], 2),
                        axis = 0,
                        mode = "wrap"
                    ),
                    device = device
                )
                for key, array in self.observations.items()
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
