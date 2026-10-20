"""
Defines the fixtures the task tests share, covering:

- The installer that puts stand-in programs first on the path
- The confinement the real `mise` runs under
- The loader that imports a Python task as a module
- The runner that reads back what the `echo.sh` stand-in printed
- The shell variables a case sets before it starts a task
"""

from collections.abc import Callable
from importlib.util  import module_from_spec, spec_from_file_location
from os              import pathsep
from pathlib         import Path
from pytest          import Config, FixtureRequest, MonkeyPatch, fixture
from shutil          import which
from subprocess      import run
from types           import ModuleType


@fixture
def confine_mise(monkeypatch: MonkeyPatch) -> Callable[[Path, Path], None]:
    """
    Builds a function that confines the real `mise` to the checkout at
    `root` and leaves only `stand_ins`, `mise`, and the system directories
    on the path. Confined there, mise reads no config above the checkout and
    trusts it under the `HOME` the `environment` fixture moves.
    """
    def confine(root: Path, stand_ins: Path):
        """
        Sets `MISE_CEILING_PATHS` to the parent of `root`,
        `MISE_TRUSTED_CONFIG_PATHS` to `root`, and `PATH` to `stand_ins`
        followed by the directory holding `mise`, `/usr/bin`, and `/bin`.
        """
        monkeypatch.setenv("MISE_CEILING_PATHS", str(root.parent))
        monkeypatch.setenv("MISE_TRUSTED_CONFIG_PATHS", str(root))
        monkeypatch.setenv(
            "PATH",
            pathsep.join(
                [str(stand_ins), str(Path(which("mise")).parent), "/usr/bin", "/bin"]
            )
        )

    return confine


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
def load_task(pytestconfig: Config) -> Callable[[str], ModuleType]:
    """
    Builds a loader that imports the task script at a path under the
    worktree root as a module named for the file's stem, so a case calls the
    records the script declares.
    """
    def load(path: str) -> ModuleType:
        """
        Imports the script at `path` under the worktree root.
        """
        spec   = spec_from_file_location(Path(path).stem, pytestconfig.rootpath / path)
        module = module_from_spec(spec)

        spec.loader.exec_module(module)

        return module

    return load


@fixture
def printed(pytestconfig: Config) -> Callable[..., list[str]]:
    """
    Builds a runner of the task file at `.mise/tasks/<task>`, which reads
    back each argument the `echo.sh` stand-in received, one per line.

    Returns:
        A function taking the task's path under `.mise/tasks` and then the
        arguments to start it with.
    """
    return lambda task, *arguments: run(
        [pytestconfig.rootpath / ".mise/tasks" / task, *arguments],
        capture_output = True,
        check          = True,
        text           = True
    ).stdout.splitlines()


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
