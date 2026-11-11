"""
Pins the wrappers under `.mise/bin`, through which each task runs a program
from the locked environment, meaning that mise puts them first on the path
from anywhere in the checkout, that each one syncs the checkout through
`uv sync --exact --locked` and then runs the program of its own name under
`.venv/bin` as its own process with every argument as given, and that every
one is the same script.

A stand-in under `fixtures/` answers for `uv` wherever a case starts it,
and each case running a wrapper copies it into a checkout of its own whose
`.venv/bin` holds the `process.sh` stand-in, so no case starts a program
from the environment.
"""

from collections.abc import Callable
from operator        import attrgetter
from os              import X_OK, access
from pathlib         import Path
from pytest          import Config, Metafunc, MonkeyPatch, fixture, mark
from shutil          import copy2
from subprocess      import PIPE, Popen, run


def pytest_generate_tests(metafunc: Metafunc):
    """
    Runs each case taking `wrapper` once per file under `.mise/bin`, so a
    wrapper added there is checked without a change to this module.
    """
    if "wrapper" in metafunc.fixturenames:
        wrappers = sorted((metafunc.config.rootpath / ".mise/bin").iterdir())
        metafunc.parametrize("wrapper", wrappers, ids=attrgetter("name"))


@fixture
def stand_in(install_stand_ins: Callable[..., Path]) -> Path:
    """
    Puts the `echo.sh` stand-in ahead of the real `uv` on the path.

    Returns:
        The directory holding the stand-in.
    """
    return install_stand_ins("echo.sh", "uv")


@fixture
def checkout(pytestconfig: Config, tmp_path: Path, wrapper: Path) -> Path:
    """
    Copies `wrapper` into the `.mise/bin` of a checkout under `tmp_path`,
    whose `.venv/bin` holds the `process.sh` stand-in under the wrapper's
    name.

    Returns:
        The copy of the wrapper.
    """
    root    = tmp_path / "checkout"
    program = root / ".venv/bin" / wrapper.name

    (root / ".mise/bin").mkdir(parents=True)
    program.parent.mkdir(parents=True)
    program.symlink_to(pytestconfig.rootpath / "tests/tasks/fixtures/process.sh")

    return Path(copy2(wrapper, root / ".mise/bin"))


def test_a_wrapper_whose_sync_fails_exits_with_its_status_before_the_program(
    checkout          : Path,
    install_stand_ins : Callable[..., Path],
    monkeypatch       : MonkeyPatch,
    tmp_path          : Path
):
    """
    Pins that a wrapper whose `uv sync` fails exits with the status `uv`
    returned and never starts the program.
    """
    calls = tmp_path / "calls"

    install_stand_ins("stand-in.sh", "uv")
    monkeypatch.setenv("CALLS", str(calls))
    monkeypatch.setenv("FAILING", "uv sync*")

    finished = run([checkout], capture_output=True, text=True)

    assert finished.returncode == 1
    assert finished.stdout == ""
    assert calls.read_text().splitlines() == [
        f"uv sync --exact --locked --project {checkout.parent}/../.. --quiet"
    ]


def test_each_wrapper_is_an_executable_copy_of_one_script(wrapper: Path):
    """
    Pins that every wrapper is a plain file rather than a symlink, holds the
    same bytes as the first file under `.mise/bin`, and is executable.
    """
    assert not wrapper.is_symlink()
    assert wrapper.read_bytes() == min(wrapper.parent.iterdir()).read_bytes()
    assert access(wrapper, X_OK)


@mark.usefixtures("stand_in")
def test_each_wrapper_syncs_and_runs_its_program_as_its_own_process(
    checkout : Path,
    tmp_path : Path
):
    """
    Pins that a wrapper started outside its checkout runs `uv sync --exact
    --locked --quiet` on the checkout's project and then replaces itself
    with the program of its own name under `.venv/bin`, keeping its process
    ID and passing every argument as given, a word holding a space among
    them.
    """
    with Popen(
        [checkout, "-k", "two words"],
        cwd    = tmp_path,
        stdout = PIPE,
        text   = True
    ) as started:
        printed = started.stdout.read().splitlines()

    assert started.returncode == 0
    assert printed[:4] == ["sync", "--exact", "--locked", "--project"]
    assert Path(printed[4]).resolve() == checkout.parents[2].resolve()
    assert printed[5:] == ["--quiet", str(started.pid), "-k", "two words"]


@mark.usefixtures("stand_in")
def test_a_wrapper_whose_program_is_missing_fails_on_its_path(checkout: Path):
    """
    Pins that a wrapper whose program is missing from `.venv/bin`, as pytest
    is under `UV_NO_DEV=1`, fails on the `exec` of that path rather than
    starting a program of the same name from the path.
    """
    (checkout.parents[2] / ".venv/bin" / checkout.name).unlink()

    finished = run([checkout], capture_output=True, text=True)

    assert finished.returncode != 0
    assert f"/.venv/bin/{checkout.name}:" in finished.stderr


def test_mise_puts_each_wrapper_first_from_a_subfolder(
    confine_mise : Callable[[Path, Path], None],
    pytestconfig : Config,
    stand_in     : Path,
    wrapper      : Path
):
    """
    Pins that the `_.path` entry in `.mise/config.toml` puts `.mise/bin` on
    the path mise hands a command run from a subfolder of the checkout, so a
    bare program name there resolves to its wrapper.

    The case runs the real `mise`, whose reading of the checkout's config is
    what it pins, confined to the checkout through `confine_mise`.
    """
    root = pytestconfig.rootpath

    confine_mise(root, stand_in)

    resolved = run(
        ["mise", "x", "--", "sh", "-c", f"command -v {wrapper.name}"],
        capture_output = True,
        check          = True,
        cwd            = root / "src/squirtl",
        text           = True
    ).stdout.strip()

    assert Path(resolved).resolve() == wrapper.resolve()
