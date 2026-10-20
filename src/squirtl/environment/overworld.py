"""
Defines `Overworld`, the environment an agent plays Pokémon Blue in from
Red's bedroom to the starter, which `Overworld.specification` specifies with
its wrappers.
"""

from functools import reduce
from gymnasium import Env
from gymnasium.envs.registration import EnvSpec
from gymnasium.spaces            import Box, Discrete
from gymnasium.wrappers          import FrameStackObservation, GrayscaleObservation, RecordEpisodeStatistics
from numpy    import ndarray, uint8
from operator import add
from typing   import Any

from squirtl.emulator.console     import GameBoy
from squirtl.emulator.schemas     import Button, Cartridge, EmulatorSettings
from squirtl.environment.schemas  import EnvironmentSettings, Recording
from squirtl.environment.wrappers import ProgressObservation, RecordOutcome, ShrinkObservation
from squirtl.reward.progress      import Progress
from squirtl.reward.schemas       import RewardSettings, Term


class Overworld(Env):
    """
    The game from Red's bedroom to the starter as a Gymnasium `Env`, whose
    actions are `presses`, whose observation is the RGB screen a step ends
    on, and whose episode terminates at the starter, each episode kept as
    the `recording` that `play` steps through again.
    """

    metadata = {"render_modes": ["rgb_array"]}

    def __init__(
        self,
        cartridge   : Cartridge,
        emulator    : EmulatorSettings,
        environment : EnvironmentSettings,
        reward      : RewardSettings,
        render_mode : str | None = None
    ):
        """
        Boots `cartridge` and plays its intro to Red's bedroom, where every
        episode starts.

        Args:
            render_mode: `rgb_array`, under which `render` returns the
                         screen, or `None` where `gymnasium.make` names
                         no mode.
        """
        self.game_boy = GameBoy.boot(cartridge, emulator)
        self.game_boy.start()

        self.action_space = Discrete(len(self.presses))
        self.metadata     = self.metadata | {"render_fps": environment.steps_per_second}
        self.observation_space = Box(0, 255, self.game_boy.screen.shape, uint8)
        self.render_mode       = render_mode
        self.reward            = reward
        self.settings          = environment

    @property
    def presses(self) -> tuple[Button | None, ...]:
        """
        Lists each action's press, `None` and then each `Button` in its
        declared order.
        """
        return (None, *Button)

    @property
    def recording(self) -> Recording:
        """
        Records the episode so far as the state its reset left the console
        in, the `timer_div` that reset wrote, and each step's action.
        """
        return Recording(
            presses   = self.actions,
            start     = self.start,
            timer_div = self.timer_div
        )

    def close(self):
        """
        Stops the emulator without saving, as `GameBoy.close` does.
        """
        self.game_boy.close()

    def play(self, recording: Recording) -> float:
        """
        Resets to the start of `recording` and steps through each action it
        holds, which the emulator plays to the frames the episode drew.

        Returns:
            The reward its steps total, each added in turn to 0.0 as
            `RecordEpisodeStatistics` adds an episode's return, where `sum`
            compensates for rounding and can differ in the last bit.
        """
        self.reset(options={"recording": recording})

        return reduce(add, (self.step(action)[1] for action in recording.presses), 0.0)

    def render(self) -> ndarray:
        """
        Copies the screen the last step or reset ended on.
        """
        return self.game_boy.screen

    def reset(
        self,
        *,
        options : dict[str, Any] | None = None,
        seed    : int | None            = None
    ) -> tuple[ndarray, dict[str, Any]]:
        """
        Loads Red's bedroom with a DIV from the environment's generator,
        which `seed` reseeds, or the start of the `Recording` that `options`
        holds under `recording`, and starts the episode's progress and its
        record. It then advances one frame with no press, since the state
        `GameBoy.start` saves holds no rendered screen.

        Returns:
            The screen that frame shows beside an empty info dict.
        """
        super().reset(seed=seed)

        match options:
            case {"recording": Recording() as recording}:
                self.game_boy.restore(recording.start)
                self.timer_div = recording.timer_div
            case _:
                # DIV holds 8 bits, so its 256 values are every start a reset gives.
                self.timer_div = int(self.np_random.integers(256))
                self.game_boy.reset(self.timer_div)

        self.actions  = bytearray()
        self.progress = Progress(self.game_boy, self.reward)
        self.start    = self.game_boy.capture()

        return self.game_boy.press(None, 1), {}

    @classmethod
    def specification(
        cls,
        cartridge   : Cartridge,
        emulator    : EmulatorSettings,
        environment : EnvironmentSettings,
        reward      : RewardSettings
    ) -> EnvSpec:
        """
        Specifies the environment for `gymnasium.make` and
        `gymnasium.make_vec`, each episode truncated at `max_episode_steps`
        through `TimeLimit` and wrapped in these, each around the
        one before:

        - `GrayscaleObservation`, `ShrinkObservation` to `frame_shape`, and
          `FrameStackObservation` of `frame_stack` frames
        - `ProgressObservation`, setting the progress beside the frames
        - `RecordEpisodeStatistics`, recording each episode's return, length,
          and time
        - `RecordOutcome`, reporting what each episode reached
        """
        return EnvSpec(
            "squirtl/Overworld-v0",
            additional_wrappers = (
                GrayscaleObservation.wrapper_spec(),
                ShrinkObservation.wrapper_spec(shape=environment.frame_shape),
                FrameStackObservation.wrapper_spec(stack_size=environment.frame_stack),
                ProgressObservation.wrapper_spec(size=environment.grid_size),
                RecordEpisodeStatistics.wrapper_spec(),
                RecordOutcome.wrapper_spec()
            ),
            entry_point = cls,
            kwargs      = {
                "cartridge"   : cartridge,
                "emulator"    : emulator,
                "environment" : environment,
                "reward"      : reward
            },
            max_episode_steps = environment.max_episode_steps
        )

    def step(self, action: int) -> tuple[ndarray, float, bool, bool, dict[Term, float]]:
        """
        Makes the press `action` names and advances `frames_per_step`
        frames, then scores the step through `Progress.score` and records
        `action` in the episode's `recording`.

        Returns:
            The five values Gymnasium's `step` returns:

            - The screen the step ends on
            - Its reward
            - Whether it found the starter
            - `False` for truncation, which `TimeLimit` reports
            - Each term's share of the reward, as the info dict
        """
        screen = self.game_boy.press(
            self.presses[action],
            self.settings.frames_per_step
        )
        score = self.progress.score()
        self.actions.append(action)

        return screen, score.total, score.terminated, False, score.shares
