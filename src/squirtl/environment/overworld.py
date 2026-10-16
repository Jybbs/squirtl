"""
Defines `Overworld`, the environment an agent plays Pokémon Blue in from
Red's bedroom to the starter, which `Overworld.make` builds and wraps.
"""

from gymnasium import Env
from gymnasium.envs.registration import EnvSpec
from gymnasium.spaces            import Box, Discrete
from gymnasium.wrappers          import FrameStackObservation, GrayscaleObservation, RecordEpisodeStatistics
from numpy  import ndarray, uint8
from typing import Any

from squirtl.emulator.console     import GameBoy
from squirtl.emulator.schemas     import Button, Cartridge, EmulatorSettings
from squirtl.environment.schemas  import EnvironmentSettings
from squirtl.environment.wrappers import ProgressObservation, ShrinkObservation
from squirtl.reward.progress      import Progress
from squirtl.reward.schemas       import RewardSettings, Term


class Overworld(Env):
    """
    The game from Red's bedroom to the starter as a Gymnasium `Env`, whose
    actions are `presses`, whose observation is the RGB screen a step ends
    on, and whose episode terminates at the starter.
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
                         screen, or `None` where `make` names no mode.
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

    def close(self):
        """
        Stops the emulator without saving, as `GameBoy.close` does.
        """
        self.game_boy.close()

    @classmethod
    def make(
        cls,
        cartridge   : Cartridge,
        emulator    : EmulatorSettings,
        environment : EnvironmentSettings,
        reward      : RewardSettings
    ) -> Env:
        """
        Builds the environment through `gymnasium.make` on an `EnvSpec`
        truncating each episode at `max_episode_steps` through `TimeLimit`,
        and wraps it in these, each around the one before:

        - `GrayscaleObservation`, `ShrinkObservation` to `frame_shape`, and
          `FrameStackObservation` of `frame_stack` frames
        - `ProgressObservation`, setting the progress beside the frames
        - `RecordEpisodeStatistics`, recording each episode's return, length,
          and time
        """
        overworld = EnvSpec(
            "squirtl/Overworld-v0",
            entry_point = cls,
            kwargs      = {
                "cartridge"   : cartridge,
                "emulator"    : emulator,
                "environment" : environment,
                "reward"      : reward
            },
            max_episode_steps = environment.max_episode_steps
        ).make()

        return RecordEpisodeStatistics(
            ProgressObservation(
                FrameStackObservation(
                    ShrinkObservation(
                        GrayscaleObservation(overworld),
                        environment.frame_shape
                    ),
                    environment.frame_stack
                ),
                environment.grid_size
            )
        )

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
        which `seed` reseeds, and starts the episode's progress. It then
        advances one frame with no press, since the state `GameBoy.start`
        saves holds no rendered screen.

        Returns:
            The bedroom's screen beside an empty info dict.
        """
        super().reset(seed=seed)
        # DIV holds 8 bits, so its 256 values are every start a reset can give the game.
        self.game_boy.reset(int(self.np_random.integers(256)))
        self.progress = Progress(self.game_boy, self.reward)

        return self.game_boy.press(None, 1), {}

    def step(self, action: int) -> tuple[ndarray, float, bool, bool, dict[Term, float]]:
        """
        Makes the press `action` names and advances `frames_per_step`
        frames, then scores the step through `Progress.score`.

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

        return screen, score.total, score.terminated, False, score.shares
