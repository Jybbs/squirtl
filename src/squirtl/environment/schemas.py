"""
Defines `EnvironmentSettings`, the settings the environment reads.
"""

from pyboy.utils import CLOCK_RATE, FRAME_CYCLES
from pydantic    import PositiveInt

from squirtl.emulator.schemas import Record


class EnvironmentSettings(Record):
    """
    The settings the environment reads, each a field of
    `RunSettings.environment` and a key under `[tool.squirtl.environment]`
    in `pyproject.toml`.
    """

    frame_shape: tuple[PositiveInt, PositiveInt] = (72, 80)
    """
    The height and width in pixels each frame is resized to, whose default
    is the grayscale screen at half its resolution that Pleines et al.
    observe.
    """

    frame_stack: PositiveInt = 4
    """
    The frames each observation stacks, the newest last, whose default
    follows Mnih et al.
    """

    frames_per_step: PositiveInt = 17
    """
    The frames each step advances from its press, whose default is the
    fewest under which a direction pressed on open ground moves the player
    one square on every press, whichever frame the press lands on.
    """

    grid_size: PositiveInt = 48
    """
    The side in squares of the grid of reached positions each observation
    centers on the player, whose default follows Pleines et al.
    """

    max_episode_steps: PositiveInt = 10_240
    """
    The steps after which `TimeLimit` truncates an episode, whose default
    is the budget Pleines et al. start each episode with.
    """

    @property
    def steps_per_second(self) -> float:
        """
        Divides the frames a second a Game Boy draws at its own speed, its
        `CLOCK_RATE` in cycles over the `FRAME_CYCLES` each frame takes, by
        `frames_per_step`.
        """
        return CLOCK_RATE / FRAME_CYCLES / self.frames_per_step
