"""
Pins the settings the environment reads, covering:

- The mean each frame takes as it shrinks, checked against a frame small
  enough to average by hand
- The frame shapes the settings refuse, each one dividing the screen
  unevenly, and the ones they keep
"""

from numpy    import array, uint8
from pydantic import ValidationError
from pytest   import mark, param, raises
from re       import escape

from squirtl.environment.schemas import EnvironmentSettings


def test_a_frame_shrinks_to_the_mean_of_each_block_rounding_a_half_up():
    """
    Asserts that a 2 by 4 frame shrinks into a 1 by 2 frame of the mean of
    each 2 by 2 block, rounding 2.5 up to 3 and 4.75 to 5, in `uint8`.
    """
    shrunk = EnvironmentSettings(frame_shape=(1, 2)).shrink(
        array([[0, 1, 2, 3], [4, 5, 6, 8]], uint8)
    )

    assert (shrunk.tolist(), shrunk.dtype) == ([[3, 5]], uint8)


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
    with raises(ValidationError, match=escape(f"a frame shape of {frame_shape} ")):
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
