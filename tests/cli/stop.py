"""
Pins what `squirtl stop` does, covering the stop file it writes into a
run's directory from the clone or from a shell outside it, and the directory
holding no run it refuses.
"""

from common.cli import Invoker
from pathlib    import Path
from pytest     import MonkeyPatch, TempPathFactory

from squirtl.runs.schemas import Run


def test_a_stop_from_a_shell_outside_the_clone_writes_the_runs_stop_file(
    invoke           : Invoker,
    monkeypatch      : MonkeyPatch,
    tmp_path_factory : TempPathFactory,
    trained          : Path
):
    """
    Asserts that `squirtl stop` given the run's absolute directory from a
    working directory outside the clone writes the stop file the run reads
    from the clone and exits zero.
    """
    stop = Run.read(trained).stop.absolute()
    monkeypatch.chdir(tmp_path_factory.mktemp("shell"))

    assert (invoke(["stop", str(stop.parent)]).code, stop.exists()) == (0, True)


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
