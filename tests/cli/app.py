"""
Pins what the `squirtl` command itself defines, meaning the help text
its metadata renders, the version that metadata carries, and the script
`[project.scripts]` points at the app.
"""

from importlib.metadata import entry_points, version
from pytest             import CaptureFixture, raises
from syrupy.assertion   import SnapshotAssertion

from squirtl.cli import app


def test_help_text(capsys: CaptureFixture[str], snapshot: SnapshotAssertion):
    """
    Asserts that `--help` exits zero and prints the help text its fixture
    file holds, carrying the description the manifest declares, so a change
    to what the command documents is reviewed as a diff.
    """
    with raises(SystemExit) as raised:
        app(["--help"])

    assert raised.value.code == 0
    assert capsys.readouterr().out == snapshot


def test_the_script_runs_this_app():
    """
    Asserts that the `squirtl` script `[project.scripts]` declares loads the
    `App` these tests drive, so the installed command runs the same app.
    """
    (script,) = entry_points(group="console_scripts", name="squirtl")

    assert script.load() is app


def test_version_reports_installed_package(capsys: CaptureFixture[str]):
    """
    Asserts that `--version` exits zero and names the installed version.
    """
    with raises(SystemExit) as raised:
        app(["--version"])

    assert raised.value.code == 0
    assert capsys.readouterr().out.strip() == version("squirtl")
