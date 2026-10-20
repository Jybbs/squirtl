"""
Defines the records the environment reads and writes:

- `Entry`, the entries of the observation the environment makes
- `EnvironmentSettings`, the settings it reads
- `Outcome`, what one episode reached, which its last step reports
- `Recording`, the start and the presses of one episode, which the emulator
  plays to the same frames again
"""

from compression.zstd    import compress, decompress
from enum                import StrEnum, auto
from functools           import partial
from pyboy.api.constants import COLS, ROWS
from pyboy.utils         import CLOCK_RATE, FRAME_CYCLES
from pydantic            import AfterValidator, Field, PlainSerializer, PositiveInt, ValidationInfo, model_validator
from typing              import Annotated, Self

from squirtl.emulator.schemas import Record
from squirtl.reward.schemas   import Term

type Compressed = Annotated[
    bytes,
    AfterValidator(validate_compressed),
    PlainSerializer(partial(compress, level=19), return_type=bytes, when_used="json")
]


def validate_compressed(value: bytes, info: ValidationInfo) -> bytes:  # prose: ignore[unsorted-positionals]
    """
    Decompresses `value` where the validation reads JSON, whose base64 the
    record's configuration has decoded, and returns it as it is otherwise,
    so a record built in Python holds the bytes it was given.
    """
    return decompress(value) if info.mode == "json" else value


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


class Outcome(Record):
    """
    What one episode reached, which `RecordOutcome` reports in the info dict
    of the episode's last step under `outcome`.
    """

    length: int
    """
    The steps the episode took.
    """

    positions: int
    """
    The number of positions the episode reached, the one it started on
    included.
    """

    reward: float
    """
    The reward the episode's steps total, its return.
    """

    seconds: float
    """
    The wall time from the episode's reset to its last step, in seconds.
    """

    shares: dict[Term, float]
    """
    Each term's part of `reward`.
    """

    terminated: bool
    """
    Whether the episode ended at the starter, where otherwise `TimeLimit`
    truncated it.
    """


class Recording(Record, ser_json_bytes="base64", val_json_bytes="base64"):
    """
    One episode as the `timer_div` its reset wrote into DIV and the action
    each step took, which the emulator plays to the same frames again, since
    a reset at one `timer_div` always leaves the console in one state. JSON
    holds the presses as the URL-safe base64 of their zstd compression at
    level 19.
    """

    presses: Compressed
    """
    The action each step took, one byte a step.
    """

    timer_div: Annotated[int, Field(ge=0, le=255)]
    """
    The value the episode's reset wrote into DIV.
    """
