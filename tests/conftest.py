"""
Defines the fixtures the suite shares, each described where it is defined.

The autouse `environment` fixture isolates every test from the machine
running it, and the collection hook lets a test open a network connection
only when it carries the `network` mark. The `rom`, `cartridge`, and
`settings` fixtures serve the tests of the emulator, the reward, and the
environment, so none needs the user's own ROM.
"""

from collections.abc   import Callable, Iterable, Iterator, Mapping
from io                import StringIO
from pathlib           import Path
from pytest            import FixtureRequest, Item, MonkeyPatch, TempPathFactory, fixture, mark
from pytest_subprocess import FakeProcess

from squirtl.emulator.schemas import Cartridge, EmulatorSettings
from squirtl.reward.schemas   import RewardSettings

CLEARED = (
    "COLORTERM", "FORCE_COLOR", "GITHUB_ACTIONS", "GITHUB_OUTPUT",
    "GITHUB_STEP_SUMMARY", "LINES", "NO_COLOR", "TTY_COMPATIBLE",
    "TTY_INTERACTIVE", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME"
)


@fixture
def answered(fp: FakeProcess, monkeypatch: MonkeyPatch) -> Callable[[str], None]:
    """
    Builds a function that types `reply` at the prompt `Plan.apply` raises,
    putting it on standard input, and has `gh api` name `Jybbs/squirtl` as
    the repository that prompt names.
    """
    def answer(reply: str):
        """
        Puts `reply` on standard input and answers the read of the
        repository's name.
        """
        fp.register(
            [
                "gh", "api", "repos/{owner}/{repo}", "--method",
                "GET", "--jq", ".full_name"
            ],
            stdout = "Jybbs/squirtl\n"
        )
        monkeypatch.setattr("sys.stdin", StringIO(reply))

    return answer


@fixture
def checkout(
    monkeypatch : MonkeyPatch,
    tmp_path    : Path
) -> Callable[[Mapping[str, str]], None]:
    """
    Builds a writer that makes `tmp_path` the working directory and writes
    each file a case names there, under its path relative to that directory.
    """
    monkeypatch.chdir(tmp_path)

    def write(files: Mapping[str, str]):
        """
        Writes each of `files`, a path beside the text it holds.
        """
        for path, text in files.items():
            (file := tmp_path / path).parent.mkdir(exist_ok=True, parents=True)
            file.write_text(text, encoding="utf-8")

    return write


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
