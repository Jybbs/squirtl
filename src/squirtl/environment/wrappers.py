"""
Defines the wrappers `Overworld.specification` names beside Gymnasium's
own, `ProgressObservation` and `ShrinkObservation`, which shape the
observation, `RecordOutcome`, which reports what each episode reached, and
`ReplayRecording`, which plays an unfinished episode back at a reset.
"""

from gymnasium        import Env, ObservationWrapper, Wrapper
from gymnasium.spaces import Box, Dict, MultiBinary
from gymnasium.utils  import RecordConstructorArgs
from numpy            import full, ndarray, ndindex, uint32, uint8
from typing           import Any

from squirtl.environment.schemas import Entry, Outcome, Recording
from squirtl.reward.schemas      import Event


class ProgressObservation(ObservationWrapper, RecordConstructorArgs):
    """
    Observes beside the stacked frames the progress the reward reads, as
    Pleines et al. observe, each entry stacked along its first axis:

    - `FLAGS`, one deep, from `Progress.flags`
    - `FRAMES`, the stack the wrapped environment observes
    - `GRID`, one deep, from `Progress.grid`, marking each position reached
    """

    def __init__(self, env: Env, size: int):
        """
        Wraps `env`, whose observation is the frame stack, with a grid
        `size` squares a side.
        """
        RecordConstructorArgs.__init__(self, size=size)
        ObservationWrapper.__init__(self, env)

        self.observation_space = Dict(
            {
                Entry.FLAGS  : MultiBinary((1, len(Event))),
                Entry.FRAMES : env.observation_space,
                Entry.GRID   : MultiBinary((1, size, size))
            }
        )
        self.size = size

    def observation(self, observation: ndarray) -> dict[Entry, ndarray]:
        """
        Sets the frame stack beside the flags and the grid of the unwrapped
        environment's `Progress`, read once the step or the reset has run.
        """
        progress = self.get_wrapper_attr("progress")

        return {
            Entry.FLAGS  : progress.flags[None],
            Entry.FRAMES : observation,
            Entry.GRID   : progress.grid(self.size)[None]
        }


class RecordOutcome(Wrapper, RecordConstructorArgs):
    """
    Reports what each episode reached as an `Outcome` in the info dict
    of its last step under `outcome`, reading the return, the length, and
    the time from the statistics `RecordEpisodeStatistics` adds beneath
    it, and the positions and the shares from the unwrapped environment's
    `Progress`, beside the episode's `Recording` under `recording`, which
    the step's info holds before an automatic reset clears it.
    """

    def __init__(self, env: Env):
        """
        Wraps `env`, which `RecordEpisodeStatistics` wraps.
        """
        RecordConstructorArgs.__init__(self)
        Wrapper.__init__(self, env)

    def step(self, action: int) -> tuple[Any, float, bool, bool, dict[str, Any]]:
        """
        Steps the wrapped environment and adds the episode's `Outcome` and
        `Recording` to the info dict once the step terminates or truncates
        it.
        """
        observation, reward, terminated, truncated, info = self.env.step(action)

        if terminated or truncated:
            progress        = self.get_wrapper_attr("progress")
            statistics      = info["episode"]
            info["outcome"] = Outcome(
                length     = statistics["l"],
                positions  = len(progress.positions),
                reward     = statistics["r"],
                seconds    = statistics["t"],
                shares     = progress.shares,
                terminated = terminated
            )
            info["recording"] = self.get_wrapper_attr("recording")

        return observation, reward, terminated, truncated, info


class ReplayRecording(Wrapper, RecordConstructorArgs):
    """
    Plays the `Recording` that `resumed` holds back through every wrapper
    beneath it at the next reset, so the frames, the step count, and the
    statistics each wrapper keeps hold what they held at the recording's
    last step, as a resumed run sets each environment back to the episode
    its checkpoint left unfinished.
    """

    def __init__(self, env: Env):
        """
        Wraps `env`, which `RecordOutcome` wraps, holding no recording.
        """
        RecordConstructorArgs.__init__(self)
        Wrapper.__init__(self, env)

        self.resumed: Recording | None = None

    def reset(
        self,
        *,
        options : dict[str, Any] | None = None,
        seed    : int | None            = None
    ) -> tuple[Any, dict[str, Any]]:
        """
        Resets the wrapped environment, or where `resumed` holds a
        recording, resets it to that recording's start and steps through
        each action the recording holds, then clears `resumed`.

        Returns:
            The observation the reset or the recording's last step ended
            on, beside an empty info dict where it played a recording back.
        """
        if (recording := self.resumed) is None:
            return self.env.reset(options=options, seed=seed)

        self.resumed   = None
        observation, _ = self.env.reset(options={"recording": recording})

        for action in recording.presses:
            observation, *_ = self.env.step(action)

        return observation, {}


class ShrinkObservation(ObservationWrapper, RecordConstructorArgs):
    """
    Shrinks each grayscale frame to `shape` by averaging the block of pixels
    each cell covers, in integers rounding a half up.
    """

    def __init__(self, env: Env, shape: tuple[int, int]):
        """
        Wraps `env`, whose grayscale frame each side of `shape` divides.
        """
        RecordConstructorArgs.__init__(self, shape=shape)
        ObservationWrapper.__init__(self, env)

        self.observation_space = Box(0, 255, shape, uint8)
        self.shape             = shape

    def observation(self, frame: ndarray) -> ndarray:
        """
        Averages each block of `frame` into its cell of `shape` by adding
        one strided slice of `frame` for each offset into a block, the slice
        holding the pixel at that offset in every block. The sum runs in
        `uint32`, which no frame the size of the screen overflows.

        Returns:
            A `shape` array of `uint8`.
        """
        rows, columns = (
            pixels // cells for pixels, cells in zip(frame.shape, self.shape)
        )
        block   = rows * columns
        offsets = ndindex(rows, columns)

        return (
            sum(
                (frame[row::rows, column::columns] for row, column in offsets),
                full(self.shape, block // 2, uint32)
            )
            // block
        ).astype(uint8)
