"""
Pins the records the environment reads and writes, covering:

- The frame shapes the settings refuse, each dividing the screen unevenly,
  and the ones they keep
- The screen and the clock the settings read, held to the ones PyBoy
  declares
- A recording's presses held as given in Python and written in JSON as the
  URL-safe base64 of their zstd compression at level 19, and the
  `timer_div` it refuses
- A recording's split into the presses a demonstration made before its
  takeover and the episode's own, and the line of a recording holding no
  takeover read back as one starting in the bedroom
- An outcome's flags written in JSON by name and read back, and a line
  holding none read back as empty
- A snapshot written in JSON and read back, its compressed bytes and its
  tally among it
"""

from base64              import urlsafe_b64decode
from common.evaluation   import outcome
from compression.zstd    import compress, decompress
from json                import loads
from pyboy.api.constants import COLS, ROWS
from pyboy.utils         import CLOCK_RATE, FRAME_CYCLES
from pydantic            import ValidationError
from pytest              import mark, param, raises
from re import escape

from squirtl.environment.schemas import EnvironmentSettings, Outcome, Recording, Snapshot, Takeover
from squirtl.reward.schemas      import Event, Position, ProgressTally, Term


@mark.parametrize(
    "frame_shape",
    [
        param((70, 80), id="a-height-144-does-not-divide"),
        param((72, 81), id="a-width-160-does-not-divide")
    ]
)
def test_the_settings_refuse_a_frame_shape_that_divides_the_screen_unevenly(
    frame_shape: tuple[int, int]
):
    """
    Asserts that the settings refuse a frame shape whose height does not
    divide the screen's 144 rows or whose width does not divide its 160
    columns, naming that shape.
    """
    with raises(
        ValidationError,
        match = escape(
            f"a frame shape of {frame_shape} does not divide the 144 by 160 screen "
            "evenly"
        )
    ):
        EnvironmentSettings(frame_shape=frame_shape)


@mark.parametrize(
    "frame_shape",
    [param((144, 160), id="the-whole-screen"), param((36, 40), id="a-quarter-of-it")]
)
def test_the_settings_keep_a_frame_shape_that_divides_the_screen(
    frame_shape: tuple[int, int]
):
    """
    Asserts that the settings keep a frame shape whose height and width each
    divide the screen's own.
    """
    assert EnvironmentSettings(frame_shape=frame_shape).frame_shape == frame_shape


def test_a_recording_reads_back_its_takeover_and_none_from_a_line_holding_none():
    """
    Asserts that a recording holding a takeover reads back as written,
    and that a line holding only presses and a `timer_div` reads back as a
    recording starting in the bedroom.
    """
    recording = Recording(
        presses  = b"\x01",
        takeover = Takeover(
            limit     = 9,
            segment   = 1,
            step      = 1,
            timer_div = 3
        ),
        timer_div = 0
    )
    bare = recording.model_dump_json(exclude={"takeover"})

    assert Recording.model_validate_json(recording.model_dump_json()) == recording
    assert Recording.model_validate_json(bare).takeover is None


def test_a_recording_writes_its_presses_as_the_base64_of_their_zstd_compression():
    """
    Asserts that a recording holds the presses it is built with, writes them
    in JSON as URL-safe base64 text that decodes to their zstd compression
    at level 19, and reads that JSON back as the recording it wrote.
    """
    recording = Recording(presses=bytes([0, 3, 6] * 40), timer_div=42)
    written   = urlsafe_b64decode(loads(recording.model_dump_json())["presses"])

    assert (written, decompress(written)) == (
        compress(recording.presses, level=19),
        recording.presses
    )
    assert Recording.model_validate_json(recording.model_dump_json()) == recording


@mark.parametrize(
    "frame_shape",
    [
        param((ROWS * 2, COLS), id="twice-the-height"),
        param((ROWS, COLS * 2), id="twice-the-width")
    ]
)
def test_the_settings_refuse_a_frame_shape_past_the_screen_pyboy_declares(
    frame_shape: tuple[int, int]
):
    """
    Asserts that the settings refuse a frame shape twice the height or the
    width of PyBoy's screen, which a literal holding a multiple of that side
    would keep.
    """
    with raises(ValidationError, match=f"{ROWS} by {COLS} screen"):
        EnvironmentSettings(frame_shape=frame_shape)


@mark.parametrize(
    "timer_div",
    [param(-1, id="below-the-register"), param(256, id="past-its-eight-bits")]
)
def test_a_recording_refuses_a_timer_div_outside_the_eight_bits_of_div(timer_div: int):
    """
    Asserts that a recording refuses a `timer_div` DIV's eight bits cannot
    hold, where 0 and 255 bound the values a reset writes.
    """
    with raises(ValidationError):
        Recording(presses=b"", timer_div=timer_div)


@mark.parametrize(
    ("takeover", "demonstrated", "played"),
    [
        param(None, b"", b"\x01\x02\x03", id="from-the-bedroom"),
        param(
            Takeover(
                limit     = 9,
                segment   = 0,
                step      = 2,
                timer_div = 0
            ),
            b"\x01\x02",
            b"\x03",
            id = "taking-over-at-step-2"
        )
    ]
)
def test_a_recording_splits_its_presses_at_its_takeover(
    demonstrated : bytes,
    played       : bytes,
    takeover     : Takeover | None
):
    """
    Asserts that a recording splits its presses into the demonstration's, up
    to its takeover's step, and the episode's own after it, none being the
    demonstration's where it holds no takeover.
    """
    recording = Recording(presses=b"\x01\x02\x03", takeover=takeover, timer_div=0)

    assert (recording.demonstrated, recording.played) == (demonstrated, played)


def test_a_snapshot_reads_back_from_json_as_the_one_written():
    """
    Asserts that a snapshot written to JSON, its compressed bytes and its
    tally included, reads back equal, as a search's checkpoint keeps it.
    """
    position = Position(map=1, x=2, y=3)
    written  = Snapshot(
        frames = bytes(range(256)),
        state  = bytes(reversed(range(256))),
        tally  = ProgressTally.of(
            {Term.NOVELTY: 2},
            {Event.EVENT_GOT_STARTER},
            {Event.EVENT_GOT_STARTER: 5},
            position,
            {position},
            5
        ),
        timer_div = 255
    )

    assert Snapshot.model_validate_json(written.model_dump_json()) == written


def test_an_outcome_writes_its_flags_by_name_and_reads_a_line_holding_none_as_empty():
    """
    Asserts that an outcome writes the step first setting each flag in
    JSON under the flag's name and reads it back as it was, whereas a line
    holding no flags reads back with none.
    """
    reached = outcome(
        flags = {Event.EVENT_FOLLOWED_OAK_INTO_LAB: 4, Event.EVENT_GOT_STARTER: 9}
    )
    line  = loads(reached.model_dump_json())
    flags = line.pop("flags")

    assert (
        flags,
        Outcome.model_validate({**line, "flags": flags}),
        Outcome(**line).flags
    ) == (
        {"EVENT_FOLLOWED_OAK_INTO_LAB": 4, "EVENT_GOT_STARTER": 9},
        reached,
        {}
    )


def test_the_settings_read_the_screen_and_the_clock_pyboy_declares():
    """
    Asserts that the settings keep a frame shape of PyBoy's `ROWS`
    by `COLS`, refuse one a row taller naming that screen, and divide
    `CLOCK_RATE` over `FRAME_CYCLES` by `frames_per_step`, so the literals
    the record holds in place of importing `pyboy` stay PyBoy's own.
    """
    settings = EnvironmentSettings(frame_shape=(ROWS, COLS), frames_per_step=2)

    assert settings.steps_per_second == CLOCK_RATE / FRAME_CYCLES / 2

    with raises(ValidationError, match=f"{ROWS} by {COLS} screen"):
        EnvironmentSettings(frame_shape=(ROWS + 1, COLS))
