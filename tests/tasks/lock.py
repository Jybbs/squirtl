"""
Pins what the `lock:check` task decides from what `uv lock --check` and
`mise lock` report, and that `.mise/mise.lock` comes back byte for byte,
mode included, whichever way the task exits.

Each case runs the task from a scratch directory holding a copy of
`.mise/mise.lock`, behind the stand-in under `fixtures/` answering for
`mise` and `uv`, which writes each call it receives to a file and answers as
the case sets, so no case reaches the network.
"""

from collections.abc import Callable
from os              import pathsep
from pathlib         import Path
from pytest          import Config, MonkeyPatch, fixture, mark
from subprocess      import CompletedProcess, run


@fixture
def calls(monkeypatch: MonkeyPatch, tmp_path: Path) -> Callable[[], list[str]]:
    """
    Puts the stand-in ahead of the real `mise` and `uv` on the path, under
    each of their names, and returns a reader of the calls it writes, one
    line each.

    The stand-in appends a line to `.mise/mise.lock` where its call matches
    the shell pattern `REWRITING` holds, prints `REPORT` to standard error
    when it answers `mise lock`, and exits 1 where its call matches the
    pattern `FAILING` holds.
    """
    received  = tmp_path / "calls"
    stand_ins = tmp_path / "stand-ins"

    stand_ins.mkdir()

    for name in ("mise", "uv"):
        (stand_ins / name).symlink_to(Path(__file__).parent / "fixtures/stand-in.sh")

    monkeypatch.setenv("CALLS", str(received))
    monkeypatch.setenv("PATH", str(stand_ins), prepend=pathsep)

    return lambda: received.read_text(encoding="utf-8").splitlines()


@fixture
def checked(
    pytestconfig : Config,
    tmp_path     : Path
) -> Callable[[], CompletedProcess[str]]:
    """
    Builds a runner of the worktree's `lock:check` task that starts it from
    `tmp_path`, capturing what it prints.
    """
    task = pytestconfig.rootpath / ".mise/tasks/lock/check"

    return lambda: run([task], capture_output=True, cwd=tmp_path, text=True)


@fixture
def lockfile(pytestconfig: Config, tmp_path: Path) -> Path:
    """
    Copies the worktree's `.mise/mise.lock` into `tmp_path` at mode `0o644`,
    which `mktemp` never gives a file, so a restore that loses the mode
    reads differently.
    """
    (tmp_path / ".mise").mkdir()

    copy = (pytestconfig.rootpath / ".mise/mise.lock").copy(
        tmp_path / ".mise/mise.lock"
    )
    copy.chmod(0o644)

    return copy


def test_a_lagging_uv_lock_stops_the_task_before_mise_lock(
    calls       : Callable[[], list[str]],
    checked     : Callable[[], CompletedProcess[str]],
    monkeypatch : MonkeyPatch
):
    """
    Pins that the task exits 1 once `uv lock --check` reports `uv.lock`
    lagging `pyproject.toml`, which it reports by exiting 1, and runs `mise
    lock` no further.
    """
    monkeypatch.setenv("FAILING", "uv lock --check")

    assert checked().returncode == 1
    assert calls() == ["uv lock --check"]


def test_a_lockfile_in_step_with_its_pins_passes(
    calls    : Callable[[], list[str]],
    checked  : Callable[[], CompletedProcess[str]],
    lockfile : Path
):
    """
    Pins that the task exits 0 once `uv lock --check` passes and `mise lock`
    leaves `.mise/mise.lock` as it found it, running the two in that order
    and leaving the file byte for byte as it was, mode included.
    """
    contents, mode = lockfile.read_bytes(), lockfile.stat().st_mode

    assert checked().returncode == 0
    assert calls() == ["uv lock --check", "mise lock"]
    assert (lockfile.read_bytes(), lockfile.stat().st_mode) == (contents, mode)


@mark.parametrize("failing", ["", "mise lock"], ids=["rewritten", "failing"])
def test_a_lockfile_mise_lock_rewrites_comes_back_whole(
    calls       : Callable[[], list[str]],
    checked     : Callable[[], CompletedProcess[str]],
    failing     : str,
    lockfile    : Path,
    monkeypatch : MonkeyPatch
):
    """
    Pins that the task exits 1 and puts `.mise/mise.lock` back byte for
    byte, mode included, when `mise lock` rewrites it, whether `mise lock`
    then exits 0 or exits 1, as it does where it cannot finish.
    """
    contents, mode = lockfile.read_bytes(), lockfile.stat().st_mode

    monkeypatch.setenv("FAILING", failing)
    monkeypatch.setenv("REWRITING", "mise lock")

    assert checked().returncode == 1
    assert (lockfile.read_bytes(), lockfile.stat().st_mode) == (contents, mode)


def test_an_unresolved_platform_fails_the_task(
    calls       : Callable[[], list[str]],
    checked     : Callable[[], CompletedProcess[str]],
    lockfile    : Path,
    monkeypatch : MonkeyPatch
):
    """
    Pins that the task exits 1 and prints the report when `mise lock`
    names a platform it failed to resolve, which `mise lock` reports while
    exiting 0 and leaving the platform's entry as it was, as it does with
    no network.
    """
    report = (
        "mise WARN  failed to resolve python for windows-x64: error sending "
        "request (version 3.14.6, and 6 more platform(s))"
    )
    monkeypatch.setenv("REPORT", report)

    result = checked()

    assert result.returncode == 1
    assert report in result.stderr
