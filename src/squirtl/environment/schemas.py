"""
Defines `EnvironmentSettings`, the settings the environment reads.
"""

from numpy               import ndarray, uint8
from pyboy.api.constants import COLS, ROWS
from pyboy.utils         import CLOCK_RATE, FRAME_CYCLES
from pydantic            import PositiveInt, model_validator
from typing              import Self

from squirtl.emulator.schemas import Record


class EnvironmentSettings(Record):
    """
    The settings the environment reads, each a field of
    `RunSettings.environment` and a key under `[tool.squirtl.environment]`
    in `pyproject.toml`.
    """

    frame_shape: tuple[PositiveInt, PositiveInt] = (72, 80)
    """
    The height and width in pixels each frame shrinks to, each dividing the
    screen's own, whose default is the grayscale screen at half its
    resolution that Pleines et al. observe.
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
    centers on the player, whose default covers one square for each of the
    48 cells a side of the crop Pleines et al. observe.
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

    def shrink(self, frame: ndarray) -> ndarray:
        """
        Shrinks a grayscale `frame` to `frame_shape` by averaging each block
        of pixels one cell covers, in integers rounding a half up.

        Returns:
            A `frame_shape` array of `uint8`.
        """
        height, width = self.frame_shape
        blocks        = frame.reshape(
            height,
            frame.shape[0] // height,
            width,
            frame.shape[1] // width
        )
        cells = blocks.shape[1] * blocks.shape[3]

        return (
            (blocks.sum(axis=(1, 3)) + cells // 2) // cells
        ).astype(uint8)

    @model_validator(mode="after")
    def verify(self) -> Self:
        """
        Refuses a `frame_shape` whose height or width does not divide the
        screen's `ROWS` by `COLS` pixels evenly, since `shrink` averages
        whole blocks.

        Raises:
            ValueError: Where either does not, which Pydantic raises as a
                        `ValidationError`.
        """
        if ROWS % self.frame_shape[0] or COLS % self.frame_shape[1]:
            raise ValueError(
                f"a frame shape of {self.frame_shape} does not divide the "
                f"{ROWS} by {COLS} screen evenly"
            )

        return self
