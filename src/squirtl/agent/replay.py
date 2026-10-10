"""
Defines `Replay`, the replay memory the agent stores each transition in and
draws each update's batch from.
"""

from numpy        import arange, count_nonzero, float32, int64, ndarray, uint8, zeros
from numpy.random import Generator
from torch        import as_tensor

from squirtl.agent.schemas import Batch


class Replay:
    """
    Replay memory over `uint8` arrays holding one frame per slot, beside
    the action taken on the stack of frames that slot ends, the reward it
    earned, and whether it terminated the episode.

    An episode's reset observation is stored whole, and every step after it
    stores only the newest frame of the observation it reaches, so the stack
    ending at a slot is the observation the policy acted on and the stack
    ending one slot later is the one the action reached. A slot holds a
    transition only where both stacks lie within one episode and no frame of
    either has been overwritten since.
    """

    def __init__(self, capacity: int, generator: Generator, shape: tuple[int, ...]):
        """
        Allocates room for `capacity` frames of an observation of `shape`,
        stacked along its first axis, drawing every batch from `generator`.
        """
        self.depth, *frame = shape

        self.actions    = zeros(capacity, int64)
        self.frames     = zeros((capacity, *frame), uint8)
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

    def begin(self, observation: ndarray):
        """
        Stores every frame of an episode's reset observation, in the order
        it stacks them.
        """
        for frame in observation:
            self.push(frame)

    def push(self, frame: ndarray):
        """
        Writes `frame` into the oldest slot, releasing each transition whose
        action was taken on a stack reading that slot.
        """
        self.held.put(self.pushed + arange(self.depth), False, mode="wrap")
        self.frames[self.pushed % len(self.frames)] = frame
        self.pushed += 1

    def sample(self, device: str, size: int) -> Batch:
        """
        Draws `size` transitions uniformly with replacement from those held,
        redrawing each draw landing on a slot that holds none, and moves
        them onto `device` as one batch.
        """
        filled = min(self.pushed, len(self.frames))
        slots  = self.generator.integers(filled, size=size)

        while (missed := ~self.held[slots]).any():
            slots[missed] = self.generator.integers(filled, size=count_nonzero(missed))

        return Batch(
            actions    = as_tensor(self.actions[slots], device=device),
            rewards    = as_tensor(self.rewards[slots], device=device),
            terminated = as_tensor(self.terminated[slots], device=device),
            window     = as_tensor(
                self.frames.take(
                    # The `depth` frames ending at each slot, then the frame after it.
                    slots[:, None] + arange(1 - self.depth, 2),
                    axis = 0,
                    mode = "wrap"
                ),
                device = device
            )
        )

    def store(
        self,
        action      : int,
        observation : ndarray,
        reward      : float,
        terminated  : bool
    ):
        """
        Records `action`, taken on the stack ending at the newest frame,
        with the `reward` it earned and whether it `terminated` the episode,
        then stores the newest frame of the `observation` it reached.
        """
        slot = (self.pushed - 1) % len(self.frames)

        self.actions[slot]    = action
        self.held[slot]       = True
        self.rewards[slot]    = reward
        self.terminated[slot] = terminated
        self.push(observation[-1])
