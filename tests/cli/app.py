"""
Pins what the `squirtl` command itself defines, meaning the help text
its metadata renders, the version that metadata carries, and the script
`[project.scripts]` points at the app, each call to the app read back as
an `Invocation`.
"""

from collections.abc    import Callable
from dataclasses        import dataclass
from importlib.metadata import EntryPoint, entry_points, version
from pytest             import CaptureFixture, fixture, raises
from syrupy.assertion   import SnapshotAssertion

from squirtl.cli import app


@dataclass(frozen=True)
class Invocation:
    """
    The status one call to the app exits with and what it prints to standard
    output.
    """

    code   : int | str | None
    output : str


@fixture
def invoke(capsys: CaptureFixture[str]) -> Callable[[list[str]], Invocation]:
    """
    Builds a caller that passes `argv` to the app and records the status it
    exits with beside what it prints.
    """
    def call(argv: list[str]) -> Invocation:
        """
        Passes `argv` to the app and reads the status it exits with beside
        what it prints to standard output.
        """
        with raises(SystemExit) as raised:
            app(argv)

        return Invocation(raised.value.code, capsys.readouterr().out)

    return call


@fixture
def script() -> EntryPoint:
    """
    Reads the one `squirtl` console script the installed distributions
    declare.
    """
    (entry,) = entry_points(group="console_scripts", name="squirtl")

    return entry


def test_the_script_runs_this_app(script: EntryPoint):
    """
    Asserts that the `squirtl` script `[project.scripts]` declares loads the
    `App` these tests drive, so the installed command runs the same app.
    """
    assert script.load() is app


def test_help_text(
    invoke   : Callable[[list[str]], Invocation],
    snapshot : SnapshotAssertion
):
    """
    Asserts that `--help` exits zero and prints the help text its fixture
    file holds, carrying the description the manifest declares, so a change
    to what the command documents is reviewed as a diff.
    """
    invocation = invoke(["--help"])

    assert invocation.code == 0
    assert invocation.output == snapshot


def test_version_reports_installed_package(
    invoke : Callable[[list[str]], Invocation],
    script : EntryPoint
):
    """
    Asserts that `--version` exits zero and names the version of the
    distribution the `squirtl` script belongs to.
    """
    invocation = invoke(["--version"])

    assert invocation.code == 0
    assert invocation.output.strip() == version(script.dist.name)
