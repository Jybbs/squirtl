"""
Pins the records the environment reads and writes, covering:

- The frame shapes the settings refuse, each dividing the screen unevenly,
  and the ones they keep
- A recording's bytes held as given in Python and written in JSON as the
  URL-safe base64 of their zstd compression, and the `timer_div` it refuses
"""

from base64           import urlsafe_b64decode
from compression.zstd import decompress
from json             import loads
from pydantic         import ValidationError
from pytest           import mark, param, raises
from re               import escape

from squirtl.environment.schemas import EnvironmentSettings, Recording


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


def test_a_recording_writes_each_bytes_field_as_the_base64_of_its_zstd_compression():
    """
    Asserts that a recording holds the bytes it is built with, writes
    each `bytes` field in JSON as URL-safe base64 text that decodes and
    decompresses to those bytes, and reads that JSON back as the recording
    it wrote.
    """
    recording = Recording(
        presses   = bytes([0, 3, 6] * 40),
        start     = b"\xab" * 512,
        timer_div = 42
    )
    written = loads(recording.model_dump_json())

    assert {key: decompress(urlsafe_b64decode(written[key])) for key in (
        "presses", "start"
    )} == {
        "presses" : recording.presses,
        "start"   : recording.start
    }
    assert Recording.model_validate_json(recording.model_dump_json()) == recording


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
        Recording(presses=b"", start=b"", timer_div=timer_div)
