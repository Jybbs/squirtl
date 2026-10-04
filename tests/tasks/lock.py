"""
Pins what the `lock:check` task decides and prints from what `uv lock
--check` and `mise lock` report, and that `.mise/mise.lock` comes back byte
for byte, mode included, whichever way the task exits.

Each case runs the task from `tmp_path`, which holds a placeholder
`.mise/mise.lock` wherever the case reaches `mise lock`, with `TMPDIR` at
the `scratch` directory inside it. The stand-in under `fixtures/` answers
for `mise` and `uv` in every case, writing each call it receives to a file
and answering as the case sets, so no case reaches the network.
"""

from collections.abc import Callable
from pathlib         import Path
from pytest          import Config, MonkeyPatch, fixture, mark
from subprocess      import CompletedProcess, run


@fixture
def calls(stand_ins: Path) -> Callable[[], list[str]]:
    """
    Builds a reader of the calls the stand-in wrote, one line each.
    """
    return lambda: stand_ins.read_text(encoding="utf-8").splitlines()


@fixture
def checked(
    pytestconfig : Config,
    scratch      : Path,
    tmp_path     : Path
) -> Callable[[], CompletedProcess[str]]:
    """
    Builds a runner of the worktree's `lock:check` task that starts it from
    `tmp_path`, capturing what it prints, with `TMPDIR` at `scratch`.
    """
    task = pytestconfig.rootpath / ".mise/tasks/lock/check"

    return lambda: run([task], capture_output=True, cwd=tmp_path, text=True)


@fixture
def lockfile(tmp_path: Path) -> Path:
    """
    Writes a placeholder `.mise/mise.lock` into `tmp_path` at mode `0o644`,
    which `mktemp` never gives a file, so a restore that loses the mode
    reads differently.
    """
    placeholder = tmp_path / ".mise/mise.lock"

    placeholder.parent.mkdir()
    placeholder.write_text("pins\n", encoding="utf-8")
    placeholder.chmod(0o644)

    return placeholder


@fixture
def scratch(monkeypatch: MonkeyPatch, tmp_path: Path) -> Path:
    """
    Makes the empty directory `mktemp` writes the snapshot into and points
    `TMPDIR` at it, so a case reads what the task leaves there.
    """
    directory = tmp_path / "scratch"

    directory.mkdir()
    monkeypatch.setenv("TMPDIR", str(directory))

    return directory


@fixture(autouse=True)
def stand_ins(
    install_stand_ins : Callable[..., Path],
    monkeypatch       : MonkeyPatch,
    tmp_path          : Path
) -> Path:
    """
    Puts the stand-in ahead of the real `mise` and `uv` on the path for
    every case, under each of their names, so no case reaches either tool.

    The stand-in appends a line to `.mise/mise.lock` where its call matches
    the shell pattern `REWRITING` holds, prints `REPORT` to standard error
    when it answers `mise lock` unless `MISE_QUIET` or `MISE_LOG_LEVEL`
    quiets it, and exits 1 where its call matches the pattern `FAILING`
    holds.

    Returns:
        The file the stand-in writes each call it receives to.
    """
    received = tmp_path / "calls"

    install_stand_ins("stand-in.sh", "mise", "uv")
    monkeypatch.setenv("CALLS", str(received))

    return received


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
    lockfile : Path,
    scratch  : Path
):
    """
    Pins that the task exits 0 once `uv lock --check` passes and `mise lock`
    leaves `.mise/mise.lock` as it found it, running the two in that order,
    leaving the file in place with its contents and inode unchanged, and
    leaving no snapshot behind.
    """
    contents, inode = lockfile.read_bytes(), lockfile.stat().st_ino

    assert checked().returncode == 0
    assert calls() == ["uv lock --check", "mise lock"]
    assert (lockfile.read_bytes(), lockfile.stat().st_ino) == (contents, inode)
    assert list(scratch.iterdir()) == []


@mark.parametrize(
    ("failing", "printed"),
    [("", "+rewritten"), ("mise lock", "mise ERROR could not write the lockfile")],
    ids = ["rewritten", "failing"]
)
def test_a_lockfile_mise_lock_rewrites_comes_back_whole(
    checked     : Callable[[], CompletedProcess[str]],
    failing     : str,
    lockfile    : Path,
    monkeypatch : MonkeyPatch,
    printed     : str
):
    """
    Pins that the task exits 1 and puts `.mise/mise.lock` back byte for
    byte, mode included, when `mise lock` rewrites it, printing the diff
    where `mise lock` then exits 0 and what `mise lock` reported where it
    exits 1, as it does where it cannot finish.
    """
    contents, mode = lockfile.read_bytes(), lockfile.stat().st_mode

    monkeypatch.setenv("FAILING", failing)
    monkeypatch.setenv("REPORT", "mise ERROR could not write the lockfile")
    monkeypatch.setenv("REWRITING", "mise lock")

    result = checked()

    assert result.returncode == 1
    assert printed in result.stderr
    assert (lockfile.read_bytes(), lockfile.stat().st_mode) == (contents, mode)


@mark.parametrize(
    "shell",
    [{}, {"MISE_QUIET": "1"}, {"MISE_LOG_LEVEL": "error"}],
    ids = ["plain", "quiet", "errors-only"]
)
def test_an_unresolved_platform_fails_the_task(
    checked     : Callable[[], CompletedProcess[str]],
    lockfile    : Path,
    monkeypatch : MonkeyPatch,
    shell       : dict[str, str]
):
    """
    Pins that the task exits 1 and prints the report when `mise lock`
    names a platform it failed to resolve, which `mise lock` reports while
    exiting 0 and leaving the platform's entry as it was, as it does with no
    network. The report holds even where the shell running the task quiets
    `mise` or narrows its log to errors, which would hide that warning.
    """
    report = (
        "mise WARN  failed to resolve python for windows-x64: error sending "
        "request (version 3.14.6, and 6 more platform(s))"
    )
    monkeypatch.setenv("REPORT", report)

    for name, value in shell.items():
        monkeypatch.setenv(name, value)

    result = checked()

    assert result.returncode == 1
    assert report in result.stderr


def test_a_missing_lockfile_leaves_no_snapshot(
    calls   : Callable[[], list[str]],
    checked : Callable[[], CompletedProcess[str]],
    scratch : Path
):
    """
    Pins that the task exits 1 without running `mise lock` when no
    `.mise/mise.lock` exists to copy, and removes the empty snapshot
    `mktemp` made before the copy failed.
    """
    assert checked().returncode == 1
    assert calls() == ["uv lock --check"]
    assert list(scratch.iterdir()) == []


def test_an_unwritable_scratch_stops_the_task_before_mise_lock(
    calls    : Callable[[], list[str]],
    checked  : Callable[[], CompletedProcess[str]],
    lockfile : Path,
    scratch  : Path
):
    """
    Pins that the task exits 1 without running `mise lock` when `mktemp`
    cannot write the snapshot into the `TMPDIR` that `scratch` sets, even
    with `.mise/mise.lock` in place to copy.
    """
    scratch.chmod(0o555)

    assert checked().returncode == 1
    assert calls() == ["uv lock --check"]
