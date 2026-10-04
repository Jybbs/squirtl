"""
Defines the fixtures the task tests share, meaning the installer that puts
stand-in programs first on the path and the shell variables a case sets
before it starts a task.
"""

from collections.abc import Callable
from os              import pathsep
from pathlib         import Path
from pytest          import Config, FixtureRequest, MonkeyPatch, fixture


@fixture
def install_stand_ins(
    monkeypatch  : MonkeyPatch,
    pytestconfig : Config,
    tmp_path     : Path
) -> Callable[..., Path]:
    """
    Builds an installer that links each program name it receives to one
    script under `tests/tasks/fixtures/`, inside `tmp_path / "stand-ins"`,
    and puts that directory first on the path until the test ends.

    Returns:
        A function taking the script's name and then the program names,
        which returns the directory holding the stand-ins.
    """
    def install(script: str, *programs: str) -> Path:
        """
        Links each of `programs` to the script named `script` and puts the
        directory holding them first on the path.
        """
        directory = tmp_path / "stand-ins"

        directory.mkdir()

        for program in programs:
            (directory / program).symlink_to(
                pytestconfig.rootpath / "tests/tasks/fixtures" / script
            )

        monkeypatch.setenv("PATH", str(directory), prepend=pathsep)

        return directory

    return install


@fixture
def shell(monkeypatch: MonkeyPatch, request: FixtureRequest) -> dict[str, str]:
    """
    Sets each variable the case's indirect `shell` row names, as the shell
    starting a task would.

    Returns:
        The variables the row names, each beside the value it took.
    """
    for name, value in request.param.items():
        monkeypatch.setenv(name, value)

    return request.param
