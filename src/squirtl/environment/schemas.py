"""
Defines the records the environment reads and writes:

- `Entry`, the entries of the observation the environment makes
- `EnvironmentSettings`, the settings it reads
- `Outcome`, what one episode reached, which its last step reports
- `Recording`, the `timer_div` and the presses of one episode, which the emulator
  plays to the same frames again, beside the `Takeover` of an episode starting
  along a demonstration
- `Starts` and `Window`, the steps of a demonstration each episode may start
  from
"""

from compression.zstd import compress, decompress
from enum             import StrEnum, auto
from functools        import partial
from pydantic         import AfterValidator, Field, NonNegativeInt, PlainSerializer, PositiveInt, ValidationInfo
from pydantic         import model_validator
from typing           import Annotated, Self

from squirtl.emulator.schemas import Record
from squirtl.reward.schemas   import Term

type Compressed = Annotated[
    bytes,
    AfterValidator(validate_compressed),
    PlainSerializer(partial(compress, level=19), return_type=bytes, when_used="json")
]

type TimerDiv = Annotated[int, Field(ge=0, le=255)]


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
        Divides the frames a Game Boy draws a second at its own speed by
        `frames_per_step`.
        """
        # Pan Docs gives a 4,194,304 Hz clock and a frame of 70,224 dots, one tick each.
        return 4_194_304 / 70_224 / self.frames_per_step

    @model_validator(mode="after")
    def verify(self) -> Self:
        """
        Refuses a `frame_shape` not dividing the screen's 144 by 160 pixels,
        since `ShrinkObservation` averages whole blocks.

        Raises:
            ValueError: Where either side does not, which Pydantic raises as
                        a `ValidationError`.
        """
        # Pan Docs gives the screen as 160 pixels wide and 144 high.
        if 144 % self.frame_shape[0] or 160 % self.frame_shape[1]:
            raise ValueError(
                f"a frame shape of {self.frame_shape} does not divide the "
                "144 by 160 screen evenly"
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


class Takeover(Record):
    """
    Where an episode starting along a demonstration took over from it, which
    its `Recording` holds beside the demonstration's presses up to that
    point.
    """

    limit: PositiveInt
    """
    The steps after which the episode truncates, set when it started.
    """

    segment: NonNegativeInt
    """
    The segment of the demonstration whose window the start was drawn from.
    """

    step: NonNegativeInt
    """
    The step of the demonstration at which the episode's own steps start.
    """

    timer_div: TimerDiv
    """
    The value the start wrote into DIV.
    """


class Recording(Record, ser_json_bytes="base64", val_json_bytes="base64"):
    """
    One episode as the `timer_div` its reset wrote into DIV and the action
    each step took, which the emulator plays to the same frames again, since
    a reset at one `timer_div` always leaves the console in one state. An
    episode starting along a demonstration holds the demonstration's presses
    up to its `takeover` ahead of its own. JSON holds the presses as the
    URL-safe base64 of their zstd compression at level 19.
    """

    presses: Compressed
    """
    The action each step took, one byte a step.
    """

    timer_div: TimerDiv
    """
    The value the episode's reset wrote into DIV.
    """

    takeover: Takeover | None = None
    """
    Where the episode took over from the demonstration it started along, or
    `None` for an episode starting in the bedroom.
    """

    @property
    def demonstrated(self) -> bytes:
        """
        Slices the presses the demonstration made before the episode took
        over, none for an episode starting in the bedroom.
        """
        return self.presses[: self.takeover.step] if self.takeover else b""

    @property
    def played(self) -> bytes:
        """
        Slices the presses the episode's own steps made.
        """
        return self.presses[len(self.demonstrated) :]


class Window(Record):
    """
    The steps of a demonstration an episode may start from to reach the end
    of one segment.
    """

    earliest: NonNegativeInt
    """
    The first step a start may be drawn at.
    """

    latest: NonNegativeInt
    """
    The last step a start may be drawn at.
    """

    segment: NonNegativeInt
    """
    The segment whose end an episode from the window aims for.
    """


class Starts(Record):
    """
    The windows the next episodes of an environment draw their starts from,
    beside the steps after which each truncates.
    """

    limit: PositiveInt
    """
    The steps after which an episode from any window truncates.
    """

    windows: list[Window]
    """
    Each segment's window, from which a start draws one segment uniformly.
    """
