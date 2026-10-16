"""
Defines the fixtures the tests of `squirtl.runs` request, meaning the
stand-in records a test reading no clone builds on, the record of one
episode, a writer of a run's episodes, the settings of a short run beside
a factory of trainers starting one, and the messages loguru logs during
a test.
"""

from collections.abc import Callable, Iterator
from contextlib      import ExitStack
from datetime        import UTC, datetime, timedelta
from itertools       import count
from loguru          import logger
from pathlib         import Path
from pytest          import MonkeyPatch, fixture

from squirtl.agent.schemas       import AgentSettings
from squirtl.emulator.schemas    import Cartridge
from squirtl.environment.schemas import EnvironmentSettings, Recording
from squirtl.reward.schemas      import Term
from squirtl.runs.schemas        import Episode, Revision, Run, RunSettings
from squirtl.runs.trainer        import Trainer


@fixture
def revision() -> Revision:
    """
    Builds the revision of a clean tree at commit `0`, with `0` as the
    digest of its lockfile, for a test that reads no clone.
    """
    return Revision(commit="0", dirty=False, lockfile="0")


@fixture
def run(revision: Revision) -> Run:
    """
    Builds a run of the default settings at `revision`, started at midnight
    UTC on 4 October 2026, for a test that writes no directory.
    """
    return Run(
        revision = revision,
        settings = RunSettings(),
        started  = datetime(2026, 10, 4, tzinfo=UTC)
    )


@fixture
def episode() -> Episode:
    """
    Builds the record of a truncated three-step episode that earned
    a novelty twice, with no update, from a start of 64 bytes and a
    `timer_div` of 9.
    """
    return Episode(
        epsilon    = 1.0,
        length     = 3,
        loss       = None,
        positions  = 3,
        recording  = Recording(presses=bytes([1, 4, 4]), start=bytes(64), timer_div=9),
        reward     = 0.125,
        seconds    = 0.5,
        shares     = {Term.MILESTONE: 0.0, Term.NOVELTY: 0.125, Term.STARTER: 0.0},
        terminated = False,
        value      = None
    )


@fixture
def short(clone: Path, rom: Path) -> RunSettings:
    """
    Builds the settings of a 20-step run in `clone` on the CPU, reading
    the cartridge `rom` writes, its episodes truncated after 6 steps, a
    checkpoint at the first episode end reaching each multiple of 10 steps,
    and each update drawing 8 transitions from 64 slots.
    """
    return RunSettings(
        agent            = AgentSettings(batch_size=8, capacity=64, device="cpu"),
        checkpoint_steps = 10,
        environment      = EnvironmentSettings(max_episode_steps=6),
        steps            = 20
    )


@fixture
def trainer(cartridge: Cartridge, short: RunSettings) -> Callable[..., Trainer]:
    """
    Builds a factory starting a run of `short`, any keyword a field of
    `RunSettings` to set in its place, and returning a trainer of that run
    on `cartridge`, each run started a second after the one before.
    """
    seconds = count()

    def build(resumes: str | None = None, **fields: object) -> Trainer:
        """
        Starts the run `fields` describe, continuing the run `resumes` names
        where it names one, and builds its trainer.
        """
        return Trainer(
            cartridge,
            Run.start(
                short.model_copy(update=fields),
                datetime(2026, 10, 4, tzinfo=UTC) + timedelta(seconds=next(seconds)),
                resumes
            )
        )

    return build


@fixture
def holding(monkeypatch: MonkeyPatch, run: Run, tmp_path: Path) -> Callable[[str], Run]:
    """
    Makes `tmp_path` the working directory and creates the directory of
    `run`, then builds a writer giving its `episodes` the text it is handed.
    """
    monkeypatch.chdir(tmp_path)
    run.directory.mkdir(parents=True)

    def write(text: str) -> Run:
        """
        Writes `text` as the run's `episodes`.

        Returns:
            The run, whose `episodes` now holds `text`.
        """
        run.episodes.write_text(text, encoding="utf-8")

        return run

    return write


@fixture
def logged() -> Iterator[list[str]]:
    """
    Adds a place loguru writes each message it logs during the test, and
    removes it once the test ends.

    Yields:
        The message of each line logged, in the order logged.
    """
    messages = []

    with ExitStack() as stack:
        stack.callback(
            logger.remove,
            logger.add(lambda line: messages.append(line.record["message"]))
        )

        yield messages
