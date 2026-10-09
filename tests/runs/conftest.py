"""
Defines the fixtures the tests of `squirtl.runs` request, meaning a git
clone in a directory the test owns, a directory no clone holds, and the
stand-in records a test reading no clone builds on.
"""

from datetime   import UTC, datetime
from os         import devnull
from pathlib    import Path
from pytest     import MonkeyPatch, fixture
from subprocess import check_call

from squirtl.runs.schemas import Revision, Run, RunSettings


@fixture
def clone(monkeypatch: MonkeyPatch, tmp_path: Path) -> Path:
    """
    Makes `tmp_path` the working directory and a git clone whose one
    commit holds a `uv.lock` and a `.gitignore` covering `data/`, as the
    repository's own `.gitignore` does.

    `GIT_CONFIG_NOSYSTEM` keeps the machine's system-wide git configuration
    out of the clone, and `GIT_CONFIG_GLOBAL` pointed at the null device
    keeps the developer's own out.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    (tmp_path / ".gitignore").write_text("/data/\n", encoding="utf-8")
    (tmp_path / "uv.lock").write_text("version = 1\n", encoding="utf-8")

    for command in (["init"], ["add", "."], ["commit", "--message", "Lock"]):
        check_call(
            [
                "git", "-c", "user.email=squirtl@example.invalid",
                "-c", "user.name=SquiRtL",
                *command
            ]
        )

    return tmp_path


@fixture
def outside(monkeypatch: MonkeyPatch, tmp_path: Path) -> Path:
    """
    Makes `tmp_path` the working directory, where `GIT_CEILING_DIRECTORIES`
    stops git looking for a clone above it, so no clone holds it.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))

    return tmp_path


@fixture
def revision() -> Revision:
    """
    Builds the revision of a clean tree at commit `0`, with `0` as the
    digest of its lockfile, for a test that reads no clone.
    """
    return Revision(commit="0", dirty=False, lockfile="0")


@fixture
def run(revision: Revision) -> Run:
    """
    Builds a run of the default settings at `revision`, started at midnight
    UTC on 4 October 2026, for a test that writes no directory.
    """
    return Run(
        revision = revision,
        settings = RunSettings(),
        started  = datetime(2026, 10, 4, tzinfo=UTC)
    )
