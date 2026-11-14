"""
Defines the fixtures the suite shares, each described where it is defined.

The autouse `environment` fixture isolates every test from the machine
running it, and the collection hook lets a test open a network connection
only when it carries the `network` mark. The `rom`, `cartridge`, `timed`,
and `settings` fixtures serve the tests of the emulator, the reward, and
the environment, so none needs the user's own ROM, `clone` serves every
test starting a run, which reads the clone it runs in, `git` every test
committing to one, `outside` every test reading a working directory no clone
holds, `evaluators` every test of a run's evaluation that starts no worker
process, `github` every test reading a release, and `pools` and `game` every
test of a search that starts none.
"""

from collections.abc   import Callable, Iterable, Iterator, Mapping
from common.console    import set_event
from common.evaluation import EvaluatorStandIn
from common.releases   import GitHub
from common.search     import PoolStandIn
from io                import StringIO
from numpy             import ndarray
from os                import devnull
from pathlib           import Path
from pytest            import FixtureRequest, Item, MonkeyPatch, TempPathFactory, fixture, mark
from pytest_subprocess import FakeProcess
from subprocess        import check_call

from squirtl.emulator.console import GameBoy
from squirtl.emulator.schemas import Button, Cartridge, EmulatorSettings, Symbol
from squirtl.reward.schemas   import Event, RewardSettings

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


@fixture
def git(monkeypatch: MonkeyPatch) -> Callable[..., None]:
    """
    Builds a runner of `git` under a placeholder author, failing on a
    nonzero exit.

    `GIT_CONFIG_NOSYSTEM` keeps the machine's system-wide git configuration
    out of every run, and `GIT_CONFIG_GLOBAL` pointed at the null device
    keeps the developer's own out.
    """
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")

    return lambda *arguments: check_call(
        [
            "git", "-c", "user.email=squirtl@example.invalid",
            "-c", "user.name=SquiRtL",
            *arguments
        ]
    )


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
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(data)
    Path(f"{path}.ram").write_bytes(b"\xab" * 0x8000)

    return path


@fixture
def timed(rom: Path) -> Cartridge:
    """
    Rewrites the cartridge `rom` writes to count each frame in the
    16 bits at `0xC000` and set flags of `wEventFlags` as the count's
    high byte passes each value, whatever the buttons pressed, so every
    episode reaches the starter after the same frames, as Pan Docs gives
    each instruction:

    - `EVENT_OAK_APPEARED_IN_PALLET` once the count reaches 256
    - `EVENT_FOLLOWED_OAK_INTO_LAB` once it reaches 512
    - `EVENT_GOT_STARTER` once it reaches 768

    Returns:
        The record of the cartridge, built as `cartridge` builds it.
    """
    program = b"".join(
        bytes.fromhex(instruction) for instruction in (
            "F0 44 FE 90 20 FA",  # Waits for LY at `0xFF44` to reach 144
            "21 00 C0 34 20 02",  # Adds 1 to the count's low byte
            "23 34",              # Adds 1 to its high byte where the low wrapped to 0
            "FA 01 C0",           # Loads the high byte into A
            "FE 01 38 05",        # Skips the next set while A is under 1
            "21 4B D7 CB FE",     # Sets bit 7 of `0xD74B`, byte 4 of `wEventFlags`
            "FE 02 38 05",        # Skips the next set while A is under 2
            "21 47 D7 CB C6",     # Sets bit 0 of `0xD747`, byte 0
            "FE 03 38 05",        # Skips the next set while A is under 3
            "21 4B D7 CB D6",     # Sets bit 2 of `0xD74B`
            "F0 44 FE 90 28 FA",  # Waits for LY to leave 144
            "18 CC"               # Jumps back to the first wait at `0x150`
        )
    )
    data              = bytearray(rom.read_bytes())
    data[0x100:0x104] = bytes.fromhex("00 C3 50 01")  # `nop`, `jp $0150`
    data[0x150 : 0x150 + len(program)] = program
    rom.write_bytes(data)

    return Cartridge.model_construct(data=bytes(data), path=rom)


@fixture
def settings() -> RewardSettings:
    """
    Builds reward settings paying powers of two apart from the defaults and
    from one another, so every sum a step earns is exact.
    """
    return RewardSettings(goal=0.5, milestone=0.125, novelty=0.0625)


@fixture
def game(monkeypatch: MonkeyPatch):
    """
    Makes every press on the cartridge `rom` writes, which holds no game,
    play one: a button moves the player right by one square more than the
    index `Button` gives it, wrapping past the last, no press stays put,
    square 16 sets `EVENT_OAK_APPEARED_IN_PALLET`, and square 64 sets
    `EVENT_GOT_STARTER`. Each press is then decided by the memory of the
    console and the button alone, so a saved state replays to the same one.
    """
    press = GameBoy.press

    def play(game_boy: GameBoy, button: Button | None, frames: int) -> ndarray:  # prose: ignore[unsorted-positionals]
        """
        Moves the player as `button` does, sets each flag the square reached
        earns, then presses as `GameBoy.press` does.
        """
        memory = game_boy.emulator.memory

        if button:
            memory[Symbol.W_X_COORD] = (
                memory[Symbol.W_X_COORD] + [*Button].index(button) + 1
            ) % 256

        if memory[Symbol.W_X_COORD] >= 16:
            set_event(Event.EVENT_OAK_APPEARED_IN_PALLET, memory)

        if memory[Symbol.W_X_COORD] >= 64:
            set_event(Event.EVENT_GOT_STARTER, memory)

        return press(game_boy, button, frames)

    monkeypatch.setattr(GameBoy, "press", play)


@fixture
def pools(monkeypatch: MonkeyPatch) -> list[PoolStandIn]:
    """
    Makes each search a run plays go through a `PoolStandIn` rather than
    worker processes on PyBoy.

    Returns:
        Each stand-in, in the order the runs built them.
    """
    built = []

    def build(**arguments: object) -> PoolStandIn:
        """
        Builds a stand-in for the pool `arguments` describe and records it.
        """
        built.append(stand_in := PoolStandIn(**arguments))

        return stand_in

    monkeypatch.setattr("squirtl.runs.searcher.ProcessPoolExecutor", build)

    return built


@fixture
def evaluators(monkeypatch: MonkeyPatch) -> list[EvaluatorStandIn]:
    """
    Makes each evaluation a run plays go through an `EvaluatorStandIn`
    rather than worker processes on PyBoy.

    Returns:
        Each stand-in, in the order the runs built them.
    """
    built = []

    def build(*arguments: object) -> EvaluatorStandIn:
        """
        Builds a stand-in for the evaluator `arguments` describe and records
        it.
        """
        built.append(stand_in := EvaluatorStandIn(*arguments))

        return stand_in

    monkeypatch.setattr("squirtl.runs.benchmark.Evaluator", build)

    return built


@fixture
def github(monkeypatch: MonkeyPatch) -> GitHub:
    """
    Makes `urlopen` in `squirtl.releases.schemas` answer through a `GitHub`
    serving nothing until a case publishes a release.
    """
    monkeypatch.setattr("squirtl.releases.schemas.urlopen", github := GitHub())

    return github


@fixture
def outside(monkeypatch: MonkeyPatch, tmp_path: Path) -> Path:
    """
    Makes `tmp_path` the working directory, where `GIT_CEILING_DIRECTORIES`
    stops git looking for a clone above it, so no clone holds it.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))

    return tmp_path


@fixture
def clone(
    checkout : Callable[[Mapping[str, str]], None],
    git      : Callable[..., None],
    tmp_path : Path
) -> Path:
    """
    Makes `tmp_path`, the working directory `checkout` sets, a git clone
    whose one commit holds a `uv.lock` and a `.gitignore` covering `data/`,
    as the repository's own `.gitignore` does.
    """
    checkout({".gitignore": "/data/\n", "uv.lock": "version = 1\n"})

    for command in (["init"], ["add", "."], ["commit", "--message", "Lock"]):
        git(*command)

    return tmp_path
