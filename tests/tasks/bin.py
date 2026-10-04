"""
Pins the wrappers under `.mise/bin`, through which each task runs a program
from the locked environment, meaning that mise puts them first on the path
from anywhere in the checkout, that each one hands `uv run` the program of
its own name under `.venv/bin` and every argument as given, and that every
one is the same script.

The stand-in under `fixtures/` answers for `uv` in every case, printing each
argument it receives on a line of its own, so no case starts a program from
the environment.
"""

from collections.abc import Callable
from operator        import attrgetter
from os              import X_OK, access, pathsep
from pathlib         import Path
from pytest          import Config, Metafunc, MonkeyPatch, fixture
from shutil          import which
from subprocess      import run


def pytest_generate_tests(metafunc: Metafunc):
    """
    Runs each case taking `wrapper` once per file under `.mise/bin`, so a
    wrapper added there is checked without a change to this module.
    """
    if "wrapper" in metafunc.fixturenames:
        wrappers = sorted((metafunc.config.rootpath / ".mise/bin").iterdir())
        metafunc.parametrize("wrapper", wrappers, ids=attrgetter("name"))


@fixture(autouse=True)
def stand_in(install_stand_ins: Callable[..., Path]) -> Path:
    """
    Puts the stand-in ahead of the real `uv` on the path for every case, so
    no case starts a program from the environment.

    Returns:
        The directory holding the stand-in.
    """
    return install_stand_ins("echo.sh", "uv")


def test_each_wrapper_hands_uv_its_program_and_arguments(
    pytestconfig : Config,
    tmp_path     : Path,
    wrapper      : Path
):
    """
    Pins that a wrapper started outside the checkout runs `uv run --exact
    --locked` on the checkout's project and the program of its own name
    under `.venv/bin`, passing every argument as given, a word holding a
    space among them.
    """
    root    = pytestconfig.rootpath.resolve()
    printed = run(
        [wrapper, "-k", "two words"],
        capture_output = True,
        check          = True,
        cwd            = tmp_path,
        text           = True
    ).stdout.splitlines()

    assert printed[:4] == ["run", "--exact", "--locked", "--project"]
    assert [Path(printed[4]).resolve(), Path(printed[5]).resolve()] == [
        root,
        root / ".venv/bin" / wrapper.name
    ]
    assert printed[6:] == ["-k", "two words"]


def test_each_wrapper_is_an_executable_copy_of_one_script(wrapper: Path):
    """
    Pins that every wrapper is a plain file rather than a symlink, holds the
    same bytes as the first file under `.mise/bin`, and is executable.
    """
    assert not wrapper.is_symlink()
    assert wrapper.read_bytes() == min(wrapper.parent.iterdir()).read_bytes()
    assert access(wrapper, X_OK)


def test_mise_puts_each_wrapper_first_from_a_subfolder(
    monkeypatch  : MonkeyPatch,
    pytestconfig : Config,
    stand_in     : Path,
    wrapper      : Path
):
    """
    Pins that the `_.path` entry in `.mise/config.toml` puts `.mise/bin` on
    the path mise hands a command run from a subfolder of the checkout, so a
    bare program name there resolves to its wrapper.

    The case runs the real `mise`, whose reading of the checkout's config
    is what it pins, on a path holding only the stand-in, `mise`, and the
    system directories. `MISE_CEILING_PATHS` stops mise at the checkout, so
    it reads no config above it, and `MISE_TRUSTED_CONFIG_PATHS` trusts the
    checkout, whose trust the `HOME` the `environment` fixture moves would
    otherwise lose.
    """
    root = pytestconfig.rootpath

    monkeypatch.setenv("MISE_CEILING_PATHS", str(root.parent))
    monkeypatch.setenv("MISE_TRUSTED_CONFIG_PATHS", str(root))
    monkeypatch.setenv(
        "PATH",
        pathsep.join(
            [str(stand_in), str(Path(which("mise")).parent), "/usr/bin", "/bin"]
        )
    )

    resolved = run(
        ["mise", "x", "--", "sh", "-c", f"command -v {wrapper.name}"],
        capture_output = True,
        check          = True,
        cwd            = root / "src/squirtl",
        text           = True
    ).stdout.strip()

    assert Path(resolved).resolve() == wrapper.resolve()
