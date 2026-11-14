"""
Defines the fixtures the tests of `squirtl.runs` request, meaning the
stand-in records a test reading no clone builds on, the record of one
episode, a writer of a run's episodes, a run holding a demonstration, the
settings of a short run beside factories of trainers starting one, a factory
of searchers on the fake game of `game` beside one on real worker processes,
and the messages loguru logs during a test.
"""

from collections.abc import Callable, Iterator, Mapping
from common.search   import PoolStandIn, finish, stop_at_thirty
from contextlib      import ExitStack
from datetime        import UTC, datetime, timedelta
from itertools       import count
from loguru          import logger
from pathlib         import Path
from pytest          import fixture

from squirtl.agent.schemas       import AgentSettings, Algorithm
from squirtl.emulator.schemas    import Cartridge
from squirtl.environment.schemas import EnvironmentSettings, Recording
from squirtl.reward.schemas      import Term
from squirtl.runs.handover       import Handover
from squirtl.runs.schemas        import Episode, Revision, Run
from squirtl.runs.searcher       import SearchHandover, Searcher
from squirtl.runs.settings       import RunSettings
from squirtl.runs.trainer        import Trainer
from squirtl.search.schemas      import SearchSettings


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
    UTC on 4 October 2026 from a state of digest `0`, for a test that writes
    no directory.
    """
    return Run(
        digest   = "0",
        revision = revision,
        settings = RunSettings(),
        started  = datetime(2026, 10, 4, tzinfo=UTC)
    )


@fixture
def demonstrated(clone: Path) -> Path:
    """
    Starts a run in `clone` the day before every run `trainer` starts, whose
    one episode reaches the starter of the cartridge `timed` writes after 13
    idle presses at a `timer_div` of 0, each advancing 64 frames.

    Returns:
        The run's directory.
    """
    run = Run.start("0", RunSettings(), datetime(2026, 10, 3, tzinfo=UTC))
    run.append(
        run.episodes,
        Episode(
            epsilon    = None,
            length     = 13,
            positions  = 1,
            recording  = Recording(presses=bytes(13), timer_div=0),
            reward     = 0.8,
            seconds    = 1.0,
            shares     = {Term.GOAL: 0.6, Term.MILESTONE: 0.2, Term.NOVELTY: 0.0},
            terminated = True,
            update     = None
        )
    )

    return run.directory


@fixture
def episode() -> Episode:
    """
    Builds the record of a truncated three-step episode that earned a
    novelty twice, with no update, from a reset at a `timer_div` of 9.
    """
    return Episode(
        epsilon    = 1.0,
        length     = 3,
        positions  = 3,
        recording  = Recording(presses=bytes([1, 4, 4]), timer_div=9),
        reward     = 0.125,
        seconds    = 0.5,
        shares     = {Term.GOAL: 0.0, Term.MILESTONE: 0.0, Term.NOVELTY: 0.125},
        terminated = False,
        update     = None
    )


@fixture
def short(clone: Path, rom: Path) -> RunSettings:
    """
    Builds the settings of a 20-step run in `clone` on the CPU, reading
    the cartridge `rom` writes, its episodes truncated after 6 steps, a
    checkpoint at the first episode end reaching each multiple of 10 steps,
    and an update every fourth step from step 8 on, drawing 8 transitions
    from 64 slots.
    """
    return RunSettings(
        agent = AgentSettings(
            batch_size   = 8,
            capacity     = 64,
            device       = "cpu",
            warmup_steps = 8
        ),
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

    def build(
        resumes   : Run | None = None,
        *,
        cartridge : Cartridge  = cartridge,
        **fields  : object
    ) -> Trainer:
        """
        Builds the trainer of the run `fields` describe on `cartridge`,
        which continues the run `resumes` from its checkpoint where it is
        one.
        """
        return Trainer.start(
            cartridge,
            short.model_copy(update=fields),
            datetime(2026, 10, 4, tzinfo=UTC) + timedelta(seconds=next(seconds)),
            resumes and Handover.from_run(resumes)
        )

    return build


def searches(cartridge: Cartridge, settings: RunSettings) -> Callable[..., Searcher]:
    """
    Builds a factory starting a search of `settings` on `cartridge`, any
    keyword a field of `RunSettings` to set in its place, each search
    started a second after the one before.
    """
    seconds = count()

    def build(resumes: Run | None = None, **fields: object) -> Searcher:
        """
        Builds the searcher of the search `fields` describe, which continues
        the search `resumes` from its checkpoint where it is one.
        """
        return Searcher(
            cartridge,
            settings.model_copy(update=fields),
            datetime(2026, 10, 4, tzinfo=UTC) + timedelta(seconds=next(seconds)),
            resumes and SearchHandover.from_run(resumes)
        )

    return build


@fixture
def searching(clone: Path, rom: Path) -> RunSettings:
    """
    Builds the settings of a 60-press search in `clone` on the CPU, reading
    the cartridge `rom` writes, of two groups of two particles, each rollout
    2 to 4 presses, each group 1 to 2 outer steps an iteration, a checkpoint
    at the first iteration end reaching each multiple of 20 presses, an
    update every 8 presses drawing 4 stacks from 64 slots, and one worker.
    """
    return RunSettings(
        agent            = AgentSettings(device="cpu"),
        checkpoint_steps = 20,
        search           = SearchSettings(
            batch_size   = 4,
            capacity     = 64,
            groups       = 2,
            inner_steps  = (2, 4),
            outer_steps  = (1, 2),
            particles    = 2,
            update_steps = 8,
            workers      = 1
        ),
        steps = 60
    )


@fixture
def searcher(
    cartridge : Cartridge,
    game      : None,
    pools     : list[PoolStandIn],
    searching : RunSettings
) -> Callable[..., Searcher]:
    """
    Builds a factory of searches of `searching` playing the fake game of
    `game` in the process running the test.
    """
    return searches(cartridge, searching)


@fixture
def halted(searcher: Callable[..., Searcher]) -> Run:
    """
    Takes a search of `searching` to the end of the first iteration reaching
    30 presses, as `squirtl stop` would stop it.

    Returns:
        The run it recorded.
    """
    return finish(searcher(), stop_at_thirty)


@fixture
def actual(cartridge: Cartridge, searching: RunSettings) -> Callable[..., Searcher]:
    """
    Builds a factory of searches of `searching` over two real worker
    processes.
    """
    return searches(
        cartridge = cartridge,
        settings  = searching.model_copy(
            update = {"search": searching.search.model_copy(update={"workers": 2})}
        )
    )


@fixture
def rolling(trainer: Callable[..., Trainer]) -> Callable[..., Trainer]:
    """
    Builds a factory starting a 32-step run of `short` under PQN or PPO,
    each of its rollouts four steps across two environments, whose eight
    samples each update splits into two minibatches.
    """

    def build(
        algorithm : Algorithm,
        *,
        agent     : Mapping[str, object] = {},
        resumes   : Run | None           = None,
        **fields  : object
    ) -> Trainer:
        """
        Builds the trainer of the run of `algorithm` that `fields` describe,
        any key of `agent` a field of `AgentSettings` to set in its place,
        which continues the run `resumes` from its checkpoint where it is
        one.
        """
        return trainer(
            resumes,
            **{
                "agent" : AgentSettings.model_validate(
                    {
                        "algorithm"    : algorithm,
                        "device"       : "cpu",
                        "environments" : 2,
                        "ppo"          : {"minibatches": 2, "rollout_steps": 4},
                        "pqn"          : {"minibatches": 2, "rollout_steps": 4}
                    } | agent
                ),
                "steps" : 32
            } | fields
        )

    return build


@fixture
def holding(
    checkout : Callable[[Mapping[str, str]], None],
    run      : Run
) -> Callable[[str], Run]:
    """
    Builds a writer giving the `episodes` of `run` the text it is handed, in
    the working directory `checkout` makes of `tmp_path`.
    """

    def write(text: str) -> Run:
        """
        Writes `text` as the run's `episodes`.

        Returns:
            The run, whose `episodes` now holds `text`.
        """
        checkout({str(run.episodes): text})

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
