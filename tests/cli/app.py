"""
Pins what the `squirtl` command itself defines, covering:

- The help text its metadata renders and the version that metadata carries,
  each call to the app read back as an `Invocation`
- The script `[project.scripts]` points at the app
- How a command reads its settings:

   - Each setting comes from its flag, then the `[tool.squirtl]` table of
     the working directory's `pyproject.toml`, then its default
   - A key no setting declares, a bare token, and a `--no-` flag are each
     refused
   - Reading the settings writes nothing
"""

from collections.abc    import Callable
from cyclopts           import App, Parameter, UnknownOptionError, UnusedCliTokensError
from dataclasses        import dataclass
from importlib.metadata import EntryPoint, entry_points, version
from pathlib            import Path
from pytest             import CaptureFixture, MonkeyPatch, fixture, mark, param, raises
from syrupy.assertion   import SnapshotAssertion
from typing             import Annotated

from squirtl.cli              import app
from squirtl.emulator.schemas import EmulatorSettings
from squirtl.reward.schemas   import RewardSettings
from squirtl.runs.schemas     import RunSettings

type Invoker = Callable[[list[str]], Invocation]
type Reader  = Callable[[list[str], str | None], RunSettings]


@dataclass(frozen=True)
class Invocation:
    """
    The status one call to the app exits with and what it prints to standard
    output.
    """

    code   : int | str | None
    output : str


@fixture
def invoke(capsys: CaptureFixture[str]) -> Invoker:
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
def read(monkeypatch: MonkeyPatch, tmp_path: Path) -> Reader:
    """
    Builds a reader that parses `argv` the way a command taking
    `RunSettings` would, through the configuration the app reads, with
    `tmp_path` as the working directory.
    """
    monkeypatch.chdir(tmp_path)
    probe = App(config=app.config, default_parameter=app.default_parameter)

    @probe.command
    def received(
        *,
        settings: Annotated[RunSettings, Parameter(name="*")] = RunSettings()
    ) -> RunSettings:
        """
        Stands in for a command taking `RunSettings`, whose result is the
        settings it receives.
        """
        return settings

    def parse(argv: list[str], manifest: str | None) -> RunSettings:
        """
        Writes `manifest` as the working directory's `pyproject.toml`
        unless it is `None`, then parses `argv` into the settings a command
        receives. A parse cyclopts rejects raises its error rather than
        exiting.
        """
        if manifest is not None:
            (tmp_path / "pyproject.toml").write_text(manifest, encoding="utf-8")

        return probe(
            ["received", *argv],
            exit_on_error = False,
            print_error   = False,
            result_action = "return_value"
        )

    return parse


@fixture
def script() -> EntryPoint:
    """
    Reads the one `squirtl` console script the installed distributions
    declare.
    """
    (entry,) = entry_points(group="console_scripts", name="squirtl")

    return entry


@mark.parametrize(
    "manifest",
    [
        param("[tool.squirtl]\nsead = 7\n", id="the-table"),
        param("[tool.squirtl.emulator]\nopen-windw = true\n", id="a-subject-table")
    ]
)
def test_a_key_no_setting_declares_is_refused(manifest: str, read: Reader):
    """
    Asserts that a key naming no setting, in the `[tool.squirtl]` table or
    in a subject's table beneath it, raises rather than leaving a misspelled
    setting at its default.
    """
    with raises(UnknownOptionError):
        read([], manifest)


def test_a_bool_setting_takes_no_negative_flag(read: Reader):
    """
    Asserts that `--emulator.no-open-window` is refused rather than read
    as `open_window = false`, since `Parameter(negative=())` in the app's
    `default_parameter` gives a setting holding a `bool` no `--no-` flag.
    """
    with raises(UnknownOptionError):
        read(["--emulator.no-open-window"], None)


def test_a_setting_takes_no_positional_token(read: Reader):
    """
    Asserts that a command taking `RunSettings` keyword-only, after a bare
    `*`, refuses a bare token rather than reading it as a setting, since
    cyclopts carries the keyword-only kind to every flattened setting,
    nested records included.
    """
    with raises(UnusedCliTokensError):
        read(["9"], None)


def test_a_table_above_the_working_directory_is_not_read(
    monkeypatch : MonkeyPatch,
    read        : Reader,
    tmp_path    : Path
):
    """
    Asserts that a `[tool.squirtl]` table in the `pyproject.toml` of a
    directory above the working directory leaves every setting at its
    default, since the app reads the working directory's manifest alone.
    """
    nested = tmp_path / "nested"
    nested.mkdir()
    monkeypatch.chdir(nested)

    assert read([], "[tool.squirtl]\nseed = 7\n") == RunSettings()


@mark.parametrize(
    ("manifest", "argv", "settings"),
    [
        param(None,                         [], RunSettings(),       id="no-manifest"),
        param("[project]\nname = 'x'\n",    [], RunSettings(),       id="no-table"),
        param("[tool.squirtl]\nseed = 7\n", [], RunSettings(seed=7), id="the-table"),
        param(
            "[tool.squirtl]\nseed = 7\n",
            ["--seed", "9"],
            RunSettings(seed=9),
            id = "a-flag-over-the-table"
        ),
        param(
            "[tool.squirtl.emulator]\nopen-window = true\n",
            ["--emulator.cartridge", "rom.gb"],
            RunSettings(
                emulator = EmulatorSettings(cartridge=Path("rom.gb"), open_window=True)
            ),
            id = "a-subject-table-beside-a-flag"
        ),
        param(
            "[tool.squirtl.reward]\nmilestone = 0.05\n",
            ["--reward.starter", "0.7"],
            RunSettings(reward=RewardSettings(milestone=0.05, starter=0.7)),
            id = "the-reward-table-beside-a-flag"
        )
    ]
)
def test_a_setting_takes_its_flag_then_the_table_then_its_default(
    argv     : list[str],
    manifest : str | None,
    read     : Reader,
    settings : RunSettings
):
    """
    Asserts that a setting takes the flag passed for it, then the same key
    in the `[tool.squirtl]` table of `pyproject.toml`, then the default its
    field declares.

    A flag for one of a subject's settings leaves in place the others that
    subject's table sets.
    """
    assert read(argv, manifest) == settings


def test_help_text(invoke: Invoker, snapshot: SnapshotAssertion):
    """
    Asserts that `--help` exits zero and prints the help text its fixture
    file holds, carrying the description the manifest declares, so a change
    to what the command documents is reviewed as a diff.
    """
    invocation = invoke(["--help"])

    assert invocation.code == 0
    assert invocation.output == snapshot


def test_reading_the_settings_writes_nothing(read: Reader, tmp_path: Path):
    """
    Asserts that reading the settings from the table and a flag writes
    nothing, leaving `pyproject.toml` the only file in the working
    directory.
    """
    read(["--seed", "9"], "[tool.squirtl]\nseed = 7\n")

    assert [path.name for path in tmp_path.iterdir()] == ["pyproject.toml"]


def test_the_script_runs_this_app(script: EntryPoint):
    """
    Asserts that the `squirtl` script `[project.scripts]` declares loads the
    `App` these tests drive, so the installed command runs the same app.
    """
    assert script.load() is app


def test_version_reports_installed_package(invoke: Invoker, script: EntryPoint):
    """
    Asserts that `--version` exits zero and names the version of the
    distribution the `squirtl` script belongs to.
    """
    invocation = invoke(["--version"])

    assert invocation.code == 0
    assert invocation.output.strip() == version(script.dist.name)
