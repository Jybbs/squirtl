"""
Defines `Overworld`, the environment an agent plays Pokémon Blue in,
from the bedroom of Blue, the player character, to the run's goal, which
`Overworld.specification` specifies with its wrappers.
"""

from functools import reduce
from gymnasium import Env
from gymnasium.envs.registration import EnvSpec
from gymnasium.spaces            import Box, Discrete
from gymnasium.wrappers          import FrameStackObservation, RecordEpisodeStatistics
from numpy    import ndarray, uint8
from operator import add
from typing   import Any

from squirtl.emulator.console     import GameBoy
from squirtl.emulator.schemas     import Button, Cartridge, EmulatorSettings
from squirtl.environment.schemas  import EnvironmentSettings, Recording
from squirtl.environment.wrappers import FollowDemonstration, ProgressObservation, RecordOutcome, ReplayRecording
from squirtl.environment.wrappers import ShrinkObservation
from squirtl.reward.progress      import Progress
from squirtl.reward.schemas       import RewardSettings, Term


class Overworld(Env):
    """
    The game from Blue's bedroom to the goal `EnvironmentSettings.goal`
    names as a Gymnasium `Env`, whose actions are `presses`, whose
    observation is the gray frame a step ends on, and whose episode
    terminates at the goal, each episode kept as the `recording` that `play`
    steps through again.
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
        Boots `cartridge` and plays its intro to Blue's bedroom, where every
        episode starts, keeping as `digest` the digest of the state the
        intro leaves, which a run records and `squirtl watch` checks.

        Args:
            render_mode: `rgb_array`, under which `render` returns the RGB
                         screen, or `None` where `gymnasium.make` names
                         no mode.
        """
        self.game_boy = GameBoy.boot(cartridge, emulator)
        self.game_boy.start()
        self.digest = self.game_boy.digest

        self.action_space = Discrete(len(self.presses))
        self.metadata     = self.metadata | {"render_fps": environment.steps_per_second}
        self.observation_space = Box(0, 255, self.game_boy.grayscale.shape, uint8)
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
        Records the episode so far as the `timer_div` its reset wrote and
        each step's action, after the presses of the demonstration it took
        over from where it started along one.
        """
        return Recording(
            presses   = self.actions,
            takeover  = self.takeover,
            timer_div = self.timer_div
        )

    def close(self):
        """
        Stops the emulator without saving, as `GameBoy.close` does.
        """
        self.game_boy.close()

    def play(self, recording: Recording) -> float:
        """
        Resets to the start of `recording` and steps through each action its
        own steps took, which the emulator plays to the frames the episode
        drew.

        Returns:
            The reward its steps total, each added in turn to 0.0 as
            `RecordEpisodeStatistics` adds an episode's return, where `sum`
            compensates for rounding and can differ in the last bit.
        """
        self.reset(options={"recording": recording})

        return reduce(add, (self.step(action)[1] for action in recording.played), 0.0)

    def render(self) -> ndarray:
        """
        Copies the RGB screen the last step or reset ended on.
        """
        return self.game_boy.screen

    def reset(
        self,
        *,
        options : dict[str, Any] | None = None,
        seed    : int | None            = None
    ) -> tuple[ndarray, dict[str, Any]]:
        """
        Starts an episode from the `Recording` that `options` holds under
        `recording`, or otherwise from Blue's bedroom at a DIV drawn from
        the environment's generator, which `seed` reseeds, and starts the
        episode's progress and its record:

        - Loads the state `options` holds under `state`, saved where the
          demonstration reached the recording's `takeover`
        - Otherwise loads Blue's bedroom with the recording's DIV, advances
          one frame with no press, since the state `GameBoy.start` saves
          holds no rendered screen, and plays the presses the demonstration
          made before the takeover
        - Writes the takeover's DIV, where the recording holds one

        Returns:
            The frame the start shows in gray beside an empty info dict.
        """
        super().reset(seed=seed)

        options = options or {}

        # DIV holds 8 bits, so its 256 values are every start a reset gives.
        recording = options.get("recording") or Recording(
            presses   = b"",
            timer_div = int(self.np_random.integers(256))
        )

        if state := options.get("state"):
            self.game_boy.load(state)
            frame = self.game_boy.grayscale
        else:
            self.game_boy.reset(recording.timer_div)
            frame = self.game_boy.press(None, 1)

            for action in recording.demonstrated:
                frame = self.game_boy.press(
                    self.presses[action],
                    self.settings.frames_per_step
                )

        if takeover := recording.takeover:
            self.game_boy.set_div(takeover.timer_div)

        self.actions   = bytearray(recording.demonstrated)
        self.progress  = Progress(self.game_boy, self.settings.goal, self.reward)
        self.takeover  = takeover
        self.timer_div = recording.timer_div

        return frame, {}

    @classmethod
    def specification(
        cls,
        cartridge     : Cartridge,
        emulator      : EmulatorSettings,
        environment   : EnvironmentSettings,
        reward        : RewardSettings,
        demonstration : Recording | None = None,
        tolerance     : float            = 0.0
    ) -> EnvSpec:
        """
        Specifies the environment for `gymnasium.make` and
        `gymnasium.make_vec`, each episode truncated at `max_episode_steps`
        through `TimeLimit` and wrapped in these, each around the
        one before:

        - `ShrinkObservation` to `frame_shape` and `FrameStackObservation`
          of `frame_stack` frames
        - `ProgressObservation`, setting the progress beside the frames
        - `FollowDemonstration`, starting each episode along `demonstration`
          under `tolerance`, where one is given
        - `RecordEpisodeStatistics`, recording each episode's return, length,
          and time
        - `RecordOutcome`, reporting what each episode reached
        - `ReplayRecording`, playing an unfinished episode back at a reset
        """
        following = (
            FollowDemonstration.wrapper_spec(
                demonstration = demonstration,
                tolerance     = tolerance
            ),
        ) if demonstration else ()

        return EnvSpec(
            "squirtl/Overworld-v0",
            additional_wrappers = (
                ShrinkObservation.wrapper_spec(shape=environment.frame_shape),
                FrameStackObservation.wrapper_spec(stack_size=environment.frame_stack),
                ProgressObservation.wrapper_spec(size=environment.grid_size),
                *following,
                RecordEpisodeStatistics.wrapper_spec(),
                RecordOutcome.wrapper_spec(),
                ReplayRecording.wrapper_spec()
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

            - The gray frame the step ends on
            - Its reward
            - Whether it first set the goal
            - `False` for truncation, which `TimeLimit` reports
            - Each term's share of the reward, as the info dict
        """
        frame = self.game_boy.press(
            self.presses[action],
            self.settings.frames_per_step
        )
        score = self.progress.score()
        self.actions.append(action)

        return frame, score.total, score.terminated, False, score.shares
