"""
Defines the fixture the tests of `squirtl.runs` request, a git clone in a
directory the test owns.
"""

from pathlib    import Path
from pytest     import MonkeyPatch, fixture
from subprocess import run


@fixture
def clone(monkeypatch: MonkeyPatch, tmp_path: Path) -> Path:
    """
    Makes `tmp_path` the working directory and a git clone whose one
    commit holds a `uv.lock` and a `.gitignore` covering `data/`, as the
    repository's own `.gitignore` does.

    `GIT_CONFIG_NOSYSTEM` keeps the machine's system-wide git configuration
    out of the clone, and the `environment` fixture's empty `HOME` keeps the
    developer's own out.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    (tmp_path / ".gitignore").write_text("/data/\n", encoding="utf-8")
    (tmp_path / "uv.lock").write_text("version = 1\n", encoding="utf-8")

    for command in (["init"], ["add", "."], ["commit", "--message", "Lock"]):
        run(
            [
                "git", "-c", "user.email=squirtl@example.invalid",
                "-c", "user.name=SquiRtL",
                *command
            ],
            capture_output = True,
            check          = True
        )

    return tmp_path
