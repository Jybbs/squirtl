"""
Defines `Entry`, the entries of the observation the environment makes, and
`EnvironmentSettings`, the settings it reads.
"""

from enum                import StrEnum, auto
from pyboy.api.constants import COLS, ROWS
from pyboy.utils         import CLOCK_RATE, FRAME_CYCLES
from pydantic            import PositiveInt, model_validator
from typing              import Self

from squirtl.emulator.schemas import Record


class Entry(StrEnum):
    """
    The entries of the environment's `Dict` observation, each valued at
    its key.
    """

    FLAGS  = auto()
    FRAMES = auto()
    GRID   = auto()


class EnvironmentSettings(Record):
    """
    The settings the environment reads, each a field of
    `RunSettings.environment` and a key under `[tool.squirtl.environment]`
    in `pyproject.toml`.
    """

    frame_shape: tuple[PositiveInt, PositiveInt] = (72, 80)
    """
    The height and width in pixels each frame shrinks to, each dividing the
    screen's own, whose default is the half-resolution grayscale screen
    Pleines et al. observe.
    """

    frame_stack: PositiveInt = 4
    """
    The frames each observation stacks, the newest last, whose default
    follows Mnih et al.
    """

    frames_per_step: PositiveInt = 17
    """
    The frames a step advances from its press, by default the fewest under
    which a direction pressed on open ground moves the player one square
    whichever frame the press lands on.
    """

    grid_size: PositiveInt = 48
    """
    The side in squares of the grid of reached positions centered on the
    player, by default one square per cell of the 48 by 48 crop Pleines et
    al. observe.
    """

    max_episode_steps: PositiveInt = 10_240
    """
    The steps after which `TimeLimit` truncates an episode, by default the
    budget Pleines et al. start each episode with.
    """

    @property
    def steps_per_second(self) -> float:
        """
        Divides the frames a Game Boy draws a second at its own speed,
        `CLOCK_RATE` over `FRAME_CYCLES`, by `frames_per_step`.
        """
        return CLOCK_RATE / FRAME_CYCLES / self.frames_per_step

    @model_validator(mode="after")
    def verify(self) -> Self:
        """
        Refuses a `frame_shape` not dividing the screen's `ROWS` by `COLS`
        pixels, since `ShrinkObservation` averages whole blocks.

        Raises:
            ValueError: Where either side does not, which Pydantic raises as
                        a `ValidationError`.
        """
        if ROWS % self.frame_shape[0] or COLS % self.frame_shape[1]:
            raise ValueError(
                f"a frame shape of {self.frame_shape} does not divide the "
                f"{ROWS} by {COLS} screen evenly"
            )

        return self
