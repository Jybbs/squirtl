"""
Pins what a training run and a search share as the loop of one run, covering
what no loop's own tests hold:

- A `Driver` naming no `step` refused
- The first step past each multiple of an interval
"""

from collections.abc import Iterator
from pathlib         import Path
from pytest          import mark, param, raises

from squirtl.runs.driver  import Driver
from squirtl.runs.schemas import Run


class Counting(Driver):
    """
    The smallest loop a test runs, reading its steps from a field.
    """

    pause = "count"

    def __init__(self, run: Run, step: int):
        """
        Starts at `step`.
        """
        super().__init__(run)

        self.count = step

    def __iter__(self) -> Iterator[int]:
        """
        Yields the count once.
        """
        yield self.count

    @property
    def checkpointed(self):
        """
        Gathers nothing.
        """

    @property
    def logs(self) -> tuple[Path, ...]:
        """
        Lists no file.
        """
        return ()

    @property
    def step(self) -> int:
        """
        Reads the count.
        """
        return self.count


def test_a_loop_naming_no_step_is_refused(run: Run):
    """
    Asserts that a subclass of `Driver` naming no `step` cannot be built.
    """
    with raises(TypeError, match="step"):
        Driver(run)


@mark.parametrize(
    ("step", "last", "due"),
    [
        param(9,  0,  False, id="short-of-the-interval"),
        param(10, 0,  True,  id="on-the-interval"),
        param(14, 10, False, id="past-the-last-one"),
        param(25, 10, True,  id="past-the-next-one")
    ]
)
def test_a_step_is_due_past_each_multiple_of_its_interval(
    due  : bool,
    last : int,
    run  : Run,
    step : int
):
    """
    Asserts that a step is due once it reaches the multiple of the interval
    after the last step that was due.
    """
    assert Counting(run, step).due(10, last) is due
