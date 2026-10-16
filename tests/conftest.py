"""
Defines the fixtures the suite shares, each described where it is defined.

The autouse `environment` fixture isolates every test from the machine
running it, and the collection hook lets a test open a network connection
only when it carries the `network` mark. The `rom`, `cartridge`, and
`settings` fixtures serve the tests of the emulator, the reward, and the
environment, so none needs the user's own ROM, and `clone` serves every test
starting a run, which reads the clone it runs in.
"""

from collections.abc  import Iterable, Iterator
from os               import devnull
from pathlib          import Path
from pytest           import FixtureRequest, Item, MonkeyPatch, TempPathFactory, fixture, mark
from subprocess       import check_call
from syrupy.assertion import SnapshotAssertion
from syrupy.extensions.single_file import SingleFileSnapshotExtension, WriteMode

from squirtl.emulator.schemas import Cartridge, EmulatorSettings
from squirtl.reward.schemas   import RewardSettings

CLEARED = (
    "COLORTERM", "FORCE_COLOR", "GITHUB_ACTIONS", "GITHUB_OUTPUT",
    "GITHUB_STEP_SUMMARY", "LINES", "NO_COLOR", "TTY_COMPATIBLE",
    "TTY_INTERACTIVE", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME"
)


class PlainFile(SingleFileSnapshotExtension):
    """
    Writes each snapshot as a plain text file at
    `fixtures/<module>/<test>.txt` beside the tests that read it, the
    `fixtures` directory named by the `--snapshot-dirname` option in
    `[tool.pytest]`.
    """

    _write_mode    = WriteMode.TEXT
    file_extension = "txt"


@fixture(params=CLEARED, scope="module")
def cleared(request: FixtureRequest) -> Iterator[str]:
    """
    Sets the variable `request.param` names, once for each name `CLEARED`
    holds, and yields that name.

    A module-scoped fixture runs before the function-scoped `environment`
    fixture, so the variable is set on every machine by the time
    `environment` clears it, a CI runner that never sets it included.
    """
    with MonkeyPatch.context() as patched:
        patched.setenv(request.param, "1")
        yield request.param


@fixture(autouse=True)
def environment(monkeypatch: MonkeyPatch, tmp_path_factory: TempPathFactory):
    """
    Clears every shell variable `CLEARED` names, any of which would let the
    machine running the suite change a result:

    - The variables that set whether a console treats its output as a
      terminal, prints color, or redraws a live display, and how many lines
      it lays out
    - `GITHUB_ACTIONS`, which a GitHub Actions runner sets to mark itself,
      and `GITHUB_OUTPUT` and `GITHUB_STEP_SUMMARY`, naming the files the
      runner collects a workflow step's outputs and a workflow run's summary
      page from
    - The XDG variables, naming the directories where a tool keeps its
      configuration, data, and state

    Sets `TERM` to `dumb`, which stops a console writing to a real terminal
    from choosing a color system, and `COLUMNS` to `80`, which every console
    a test builds reads as its width before the size of any terminal the
    suite runs in. It points `HOME` at an empty directory the test owns, so
    a tool that falls back to `~` finds none of the developer's files there.
    """
    for name in CLEARED:
        monkeypatch.delenv(name, raising=False)

    monkeypatch.setenv("COLUMNS", "80")
    monkeypatch.setenv("HOME", str(tmp_path_factory.mktemp("home")))
    monkeypatch.setenv("TERM", "dumb")


def pytest_collection_modifyitems(items: Iterable[Item]):
    """
    Adds pytest-socket's `enable_socket` mark to every test carrying the
    `network` mark. The `--disable-socket` option in `addopts` blocks every
    test from opening a connection, and a test carrying `enable_socket` can
    reach a live service again.
    """
    for item in items:
        if item.get_closest_marker("network"):
            item.add_marker(mark.enable_socket)


@fixture
def snapshot(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    """
    Routes every snapshot through the plain-file extension.
    """
    return snapshot.use_extension(PlainFile)


@fixture
def cartridge(rom: Path) -> Cartridge:
    """
    Builds the record of the cartridge `rom` writes without the check
    `Cartridge.read` runs, since pret/pokered lists no digest of that ROM.
    """
    return Cartridge.model_construct(data=rom.read_bytes(), path=rom)


@fixture
def rom(tmp_path: Path) -> Path:
    """
    Writes a 32 KiB cartridge holding no game at the path `EmulatorSettings`
    reads by default under `tmp_path`, its header checksummed as Pan Docs
    gives so PyBoy boots it into one loop. Beside it sits the save PyBoy
    reads for that path, holding `0xAB` in each of its 32 KiB.
    """
    data              = bytearray(0x8000)
    data[0x100:0x102] = b"\x18\xfe"      # `jr @`, a relative jump back onto itself
    data[0x147:0x14A] = b"\x13\x00\x03"  # MBC3+RAM+BATTERY, 32 KiB of ROM and of RAM
    data[0x14D]       = -sum(byte + 1 for byte in data[0x134:0x14D]) % 256

    path = tmp_path / EmulatorSettings().cartridge
    path.parent.mkdir()
    path.write_bytes(data)
    Path(f"{path}.ram").write_bytes(b"\xab" * 0x8000)

    return path


@fixture
def settings() -> RewardSettings:
    """
    Builds reward settings paying powers of two apart from the defaults and
    from one another, so every sum a step earns is exact.
    """
    return RewardSettings(milestone=0.125, novelty=0.0625, starter=0.5)


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
