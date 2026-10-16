"""
Pins what `squirtl stop` does, covering the stop file it writes into a run's
directory and the directory holding no run it refuses.
"""

from common.cli import Invoker
from pathlib    import Path

from squirtl.runs.schemas import Run


def test_a_stop_of_a_directory_holding_no_run_exits_1_and_writes_nothing(
    clone  : Path,
    invoke : Invoker
):
    """
    Asserts that `squirtl stop` given a directory holding no run exits 1 and
    writes nothing into it.
    """
    (clone / "data").mkdir()

    assert (invoke(["stop", "data"]).code, list((clone / "data").iterdir())) == (1, [])


def test_a_stop_writes_the_runs_stop_file_and_exits_zero(
    invoke  : Invoker,
    trained : Path
):
    """
    Asserts that `squirtl stop` writes the stop file the run reads at each
    episode's end into the run's directory and exits zero.
    """
    invocation = invoke(["stop", str(trained)])

    assert (invocation.code, Run.read(trained).stop.exists()) == (0, True)
