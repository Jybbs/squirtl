"""
Defines the fixtures the tests of `squirtl.cli` request:

- `invoke`, which calls the app and reads back its `Invocation`
- `accepted`, under which a cartridge passes the check of its digest
- `quick`, the flags of a short run on the CPU, and `trained`, a run
  `squirtl train` takes through under them
- `windows`, under which PyBoy draws no window whichever one a boot names,
  recording the one each boot named
"""

from common.cli import Invocation, Invoker
from pathlib    import Path
from pyboy      import PyBoy
from pytest     import CaptureFixture, MonkeyPatch, fixture, raises

from squirtl.cli              import app
from squirtl.emulator         import console
from squirtl.emulator.schemas import Cartridge


@fixture
def accepted(monkeypatch: MonkeyPatch):
    """
    Makes `Cartridge.read` build the record of whatever file it reads
    without the check of its digest, since pret/pokered lists no digest of
    the cartridge `rom` writes.
    """
    monkeypatch.setattr(
        Cartridge,
        "read",
        classmethod(
            lambda cls, path: cls.model_construct(data=path.read_bytes(), path=path)
        )
    )


@fixture
def invoke(capsys: CaptureFixture[str]) -> Invoker:
    """
    Builds a caller that passes `argv` to the app and records the status it
    exits with beside what it prints and what it logs.
    """

    def call(argv: list[str]) -> Invocation:
        """
        Passes `argv` to the app and reads the status it exits with beside
        what it prints to standard output and to standard error.
        """
        with raises(SystemExit) as raised:
            app(argv)

        captured = capsys.readouterr()

        return Invocation(raised.value.code, captured.err, captured.out)

    return call


@fixture
def windows(monkeypatch: MonkeyPatch) -> list[str]:
    """
    Makes every boot draw no window, whichever window `GameBoy.boot` names,
    so a command opening one runs headless under the suite.

    Returns:
        The window each boot named, in the order the boots ran.
    """
    named = []

    def boot(gamerom: object, **options: object) -> PyBoy:
        """
        Records the window `options` names and boots PyBoy drawing none.
        """
        named.append(options["window"])

        return PyBoy(gamerom, **options | {"window": "null"})

    monkeypatch.setattr(console, "PyBoy", boot)

    return named


@fixture
def quick() -> list[str]:
    """
    Builds the flags of a 10-step run on the CPU, its episodes truncated
    after 4 steps, a checkpoint every 4 steps, and each update drawing 4
    transitions from 64 slots.
    """
    return [
        "--agent.batch-size", "4", "--agent.capacity", "64",
        "--agent.device", "cpu", "--checkpoint-steps", "4",
        "--environment.max-episode-steps", "4", "--steps", "10"
    ]


@fixture
def trained(
    accepted : None,
    clone    : Path,
    invoke   : Invoker,
    quick    : list[str],
    rom      : Path
) -> Path:
    """
    Takes a run of `quick` through `squirtl train` in `clone` on the
    cartridge `rom` writes, which `accepted` lets past its digest.

    Returns:
        The run's directory, which the command prints.
    """
    return Path(invoke(["train", *quick]).output.strip())
