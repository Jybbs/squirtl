"""
Pins the settings the environment reads, covering:

- The mean each frame takes as it shrinks, checked against frames small
  enough to average by hand, in square blocks and in oblong ones
- The frame shapes the settings refuse, each one dividing the screen
  unevenly, and the ones they keep
"""

from numpy    import array, uint8
from pydantic import ValidationError
from pytest   import mark, param, raises
from re       import escape

from squirtl.environment.schemas import EnvironmentSettings


@mark.parametrize(
    ("frame", "frame_shape", "shrunk"),
    [
        param(
            [[0, 1, 2, 3], [4, 5, 6, 8], [255, 255, 9, 9], [255, 254, 9, 10]],
            (2, 2),
            [[3, 5], [255, 9]],
            id = "blocks-of-2-by-2"
        ),
        param(
            [[0, 1, 2, 3, 4, 5], [6, 7, 8, 9, 10, 14]],
            (1, 2),
            [[4, 8]],
            id = "blocks-of-2-by-3"
        )
    ]
)
def test_a_frame_shrinks_to_the_mean_of_each_block_rounding_a_half_up(
    frame       : list[list[int]],
    frame_shape : tuple[int, int],
    shrunk      : list[list[int]]
):
    """
    Asserts that a frame shrinks into `frame_shape` cells of `uint8`, each
    the mean of the block of pixels it covers with a half rounded up, so 2.5
    becomes 3, 7.5 becomes 8, and 9.25 becomes 9, whether a block is square
    or oblong, with no sum overflowing near 255 and no block taking in the
    pixels of its neighbors.
    """
    result = EnvironmentSettings(frame_shape=frame_shape).shrink(array(frame, uint8))

    assert (result.tolist(), result.dtype) == (shrunk, uint8)


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
