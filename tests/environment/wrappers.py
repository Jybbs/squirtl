"""
Pins the mean `ShrinkObservation` takes over each block of a frame, checked
against frames small enough to average by hand, in square blocks and in
oblong ones.
"""

from numpy  import array, uint8
from pytest import mark, param

from squirtl.environment.overworld import Overworld
from squirtl.environment.wrappers  import ShrinkObservation


@mark.parametrize(
    ("frame", "shape", "shrunk"),
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
    frame     : list[list[int]],
    overworld : Overworld,
    shape     : tuple[int, int],
    shrunk    : list[list[int]]
):
    """
    Asserts that a frame shrinks into `shape` cells of `uint8`, each the
    mean of its block with a half rounded up, so 2.5 becomes 3, 7.5 becomes
    8, and 9.25 becomes 9, square or oblong, with no sum overflowing near
    255 and no block taking in its neighbors' pixels.
    """
    result = ShrinkObservation(overworld, shape).observation(array(frame, uint8))

    assert (result.tolist(), result.dtype) == (shrunk, uint8)
