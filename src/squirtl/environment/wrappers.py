"""
Defines the wrappers `Overworld.specification` names beside Gymnasium's
own, `ProgressObservation` and `ShrinkObservation`, which shape the
observation, `FollowDemonstration`, which starts each episode along a
demonstration, `RecordOutcome`, which reports what each episode reached, and
`ReplayRecording`, which plays an unfinished episode back at a reset.
"""

from collections      import Counter
from compression.zstd import compress, decompress
from functools        import cached_property
from gymnasium        import Env, ObservationWrapper, Wrapper
from gymnasium.spaces import Box, Dict, MultiBinary
from gymnasium.utils  import RecordConstructorArgs, seeding
from itertools        import pairwise
from numpy            import full, ndarray, ndindex, uint32, uint8
from typing           import Any

from squirtl.environment.schemas import Entry, Outcome, Recording, Starts, Takeover
from squirtl.reward.schemas      import Event, Term


class FollowDemonstration(Wrapper, RecordConstructorArgs):
    """
    Starts each episode at a step of `demonstration` drawn from the `starts`
    the trainer sets, or in Blue's bedroom where it sets none, as Mhammedi
    and Cohan's Appendix B starts each episode after Salimans and Chen. It
    plays the demonstration once as it wraps the environment, keeping at
    each step the console's state compressed through zstd, the frames the
    observation stacks, and the terms earned so far, and splits it into
    segments, each ending at the step that first sets one of the flags
    `Event` names.

    An episode from a start succeeds once the reward for the flags it sets
    reaches what the demonstration earned for them from the same step to its
    segment's end, less `tolerance`, which truncates it, as do the `limit`
    steps its start allows.
    """

    def __init__(self, env: Env, *, demonstration: Recording, tolerance: float):
        """
        Wraps `env`, which `ProgressObservation` wraps, and plays
        `demonstration` through it.

        Raises:
            ValueError: Where `demonstration` no longer reaches the starter
                        at its last press.
        """
        RecordConstructorArgs.__init__(
            self,
            demonstration = demonstration,
            tolerance     = tolerance
        )
        Wrapper.__init__(self, env)

        self.demonstration = demonstration
        self.earned   : list[Counter[Term]] = []
        self.stacks   : list[ndarray]       = []
        self.starts   : Starts | None       = None
        self.states   : list[bytes]         = []
        self.takeover : Takeover | None     = None
        self.tolerance = tolerance

        self.follow()

    @cached_property
    def ends(self) -> list[int]:
        """
        Lists the step of the demonstration whose press first sets each
        flag, in the order the demonstration sets them, each the end of
        one segment.
        """
        return [
            step for step, (before, after) in enumerate(pairwise(self.earned))
            if (after - before).keys() - {Term.NOVELTY}
        ]

    def draw(self, starts: Starts) -> Takeover:
        """
        Draws a takeover from `starts` through the environment's generator,
        a segment uniformly among its windows, a step uniformly within that
        window, and a `timer_div` uniformly among DIV's 256 values.
        """
        window = starts.windows[self.np_random.integers(len(starts.windows))]

        return Takeover(
            limit   = starts.limit,
            segment = window.segment,
            step    = int(self.np_random.integers(window.earliest, window.latest + 1)),
            timer_div = int(self.np_random.integers(256))
        )

    def follow(self):
        """
        Plays the demonstration from Blue's bedroom, keeping before each
        press the console's state compressed through zstd, the observation's
        stacked frames, and the terms earned so far, and after the last
        press the terms earned.

        Raises:
            ValueError: Where an episode ends before the last press, or the
                        last press does not reach the starter.
        """
        presses        = self.demonstration.presses
        observation, _ = self.env.reset(
            options = {
                "recording": Recording(
                    presses   = b"",
                    timer_div = self.demonstration.timer_div
                )
            }
        )
        terminated = truncated = False

        for action in presses:
            if terminated or truncated:
                break

            self.earned.append(Counter(self.get_wrapper_attr("progress").earned))
            self.stacks.append(observation[Entry.FRAMES])
            self.states.append(compress(self.get_wrapper_attr("game_boy").state))

            observation, _, terminated, truncated, _ = self.env.step(action)

        self.earned.append(Counter(self.get_wrapper_attr("progress").earned))

        if not terminated or len(self.states) < len(presses):
            raise ValueError(
                f"the demonstration's {len(presses):,} presses no longer reach the "
                f"starter at the last of them"
            )

    def reset(
        self,
        *,
        options : dict[str, Any] | None = None,
        seed    : int | None            = None
    ) -> tuple[Any, dict[str, Any]]:
        """
        Starts the episode at the first of these that applies:

        - The takeover of the `Recording` that `options` holds under
          `recording`, as a resumed run plays one back
        - A takeover `draw` takes from `starts`, once `seed` reseeds the
          environment's generator where one is given
        - Blue's bedroom, the wrapped environment's own reset

        Returns:
            The observation at the start, whose stacked frames are those the
            demonstration's observation stacked there, beside the info dict
            of the wrapped environment's reset.
        """
        match options:
            case {"recording": Recording(takeover=Takeover() as takeover) as recording}:
                pass
            case _ if self.starts:
                if seed is not None:
                    self.np_random, _ = seeding.np_random(seed)

                takeover  = self.draw(self.starts)
                recording = Recording(
                    presses   = self.demonstration.presses[: takeover.step],
                    takeover  = takeover,
                    timer_div = self.demonstration.timer_div
                )
            case _:
                self.takeover = None

                return self.env.reset(options=options, seed=seed)

        stack         = self.stacks[takeover.step]
        self.steps    = 0
        self.takeover = takeover
        self.target   = self.get_wrapper_attr("reward").goal(
            self.earned[self.ends[takeover.segment] + 1] - self.earned[takeover.step]
        ) - self.tolerance

        observation, info = self.env.reset(
            options = {
                "recording" : recording,
                "state"     : decompress(self.states[takeover.step])
            }
        )
        self.get_wrapper_attr("obs_queue").extend(stack)

        return observation | {Entry.FRAMES: stack.copy()}, info

    def step(self, action: int) -> tuple[Any, float, bool, bool, dict[str, Any]]:
        """
        Steps the wrapped environment, and for an episode started along the
        demonstration, truncates it once it succeeds or takes the `limit`
        steps its start allows, reporting at its last step whether it
        succeeded under `succeeded` in the info dict.
        """
        observation, reward, terminated, truncated, info = self.env.step(action)

        if takeover := self.takeover:
            self.steps += 1
            earned      = self.get_wrapper_attr("progress").earned
            succeeded   = self.get_wrapper_attr("reward").goal(earned) >= self.target
            truncated  |= not terminated and (succeeded or self.steps >= takeover.limit)

            if terminated or truncated:
                info["succeeded"] = succeeded

        return observation, reward, terminated, truncated, info


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

        for action in recording.played:
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
