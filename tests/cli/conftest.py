"""
Defines the fixtures the tests of `squirtl.cli` request:

- `invoke`, which calls the app and reads back its `Invocation`
- `accepted`, under which a cartridge passes the check of its digest
- `quick`, the flags of a short run on the CPU evaluating two episodes,
  `trained`, a run `squirtl train` takes through under them, and
  `stopped`, one it stops at the end of an episode short of its steps
- `rolling`, a factory of the flags of a short run of PQN or PPO, and `rolled`,
  a run of either that `squirtl train` takes through under them
- `brief`, the flags of a short search on the CPU, `searched`, a search
  `squirtl search` takes through under them, `found`, one it takes on to
  its goal, and `halted`, one it stops at the end of an iteration short of
  its steps
- `windows`, under which PyBoy draws no window whichever one a boot names,
  recording the one each boot named
- `released`, the run `trained` holds as a release `github` publishes
  attaches it
"""

from collections.abc import Callable
from common.cli      import Invocation, Invoker
from common.releases import GitHub
from common.search   import PoolStandIn
from pathlib         import Path
from pyboy           import PyBoy
from pytest          import CaptureFixture, FixtureRequest, MonkeyPatch, fixture, raises

from squirtl.cli              import app
from squirtl.emulator         import console
from squirtl.emulator.schemas import Cartridge
from squirtl.releases.schemas import ReleaseManifest, ReleaseSettings
from squirtl.runs.searcher    import Searcher
from squirtl.runs.trainer     import Trainer


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
    after 4 steps, a checkpoint every 4 steps, an update every fourth step
    from step 4 on drawing 4 transitions from 64 slots, and each evaluation
    playing 2 episodes in 2 environments.
    """
    return [
        "--agent.batch-size", "4", "--agent.capacity", "64", "--agent.device",
        "cpu", "--agent.warmup-steps", "4", "--checkpoint-steps", "4",
        "--environment.max-episode-steps", "4", "--evaluation.environments", "2",
        "--evaluation.episodes", "2", "--steps", "10"
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


@fixture
def rolling() -> Callable[[str], list[str]]:
    """
    Builds a factory of the flags of a 16-step run of the agent it is handed
    on the CPU across 2 environments, its rollouts of 4 steps splitting into
    2 minibatches, its episodes truncated after 3 steps, a checkpoint every
    8 steps, and each evaluation playing 2 episodes in 2 environments.
    """
    return lambda algorithm: [
        "--agent.algorithm", algorithm, "--agent.device", "cpu",
        "--agent.environments", "2", "--agent.ppo.minibatches", "2",
        "--agent.ppo.rollout-steps", "4", "--agent.pqn.minibatches", "2",
        "--agent.pqn.rollout-steps", "4", "--checkpoint-steps", "8",
        "--environment.max-episode-steps", "3", "--evaluation.environments", "2",
        "--evaluation.episodes", "2", "--steps", "16"
    ]


@fixture(params=["ppo", "pqn"])
def rolled(
    accepted : None,
    clone    : Path,
    invoke   : Invoker,
    request  : FixtureRequest,
    rolling  : Callable[[str], list[str]],
    rom      : Path
) -> Path:
    """
    Takes a run of PPO and a run of PQN through `squirtl train` in `clone`
    on the cartridge `rom` writes, which `accepted` lets past its digest.

    Returns:
        The run's directory, which the command prints.
    """
    return Path(invoke(["train", *rolling(request.param)]).output.strip())


@fixture
def stopped(
    accepted    : None,
    clone       : Path,
    invoke      : Invoker,
    monkeypatch : MonkeyPatch,
    quick       : list[str],
    rom         : Path
) -> Path:
    """
    Takes a run of `quick` through `squirtl train` in `clone`, stopping it
    at the end of its second episode on step 8, short of its ten steps, as
    `squirtl stop` would.

    Returns:
        The run's directory, which the command prints.
    """
    with monkeypatch.context() as patch:
        patch.setattr(
            Trainer,
            "stopping",
            property(lambda trainer: trainer.agent.step >= 8)
        )

        return Path(invoke(["train", *quick]).output.strip())


@fixture
def released(github: GitHub, trained: Path) -> Path:
    """
    Lists the run `trained` holds under `docs/runs/`, packs it as the
    recommended run, publishes the release `0.2.0` attaching each file
    the pack wrote, and moves the run's directory to `data/packed/`, so a
    command reading the release fetches it.

    Returns:
        The directory the run is fetched into.
    """
    Path("docs/runs", trained.name).mkdir(parents=True)
    github.publish(
        ReleaseManifest.pack(ReleaseSettings(recommended_run=trained.name))
    )
    trained.rename(Path("data/packed"))

    return trained


@fixture
def brief() -> list[str]:
    """
    Builds the flags of a 40-press search on the CPU of two groups of two
    particles, each rollout 2 to 4 presses, each group 1 to 2 outer steps
    an iteration, a checkpoint every 20 presses, an update every 8 presses
    drawing 4 stacks from 64 slots, and one worker.
    """
    return [
        "--agent.device", "cpu", "--checkpoint-steps", "20", "--search.batch-size", "4",
        "--search.capacity", "64", "--search.groups", "2", "--search.inner-steps", "2",
        "4", "--search.outer-steps", "1", "2", "--search.particles", "2",
        "--search.update-steps", "8", "--search.workers", "1", "--steps", "40"
    ]


@fixture
def searched(
    accepted : None,
    brief    : list[str],
    clone    : Path,
    game     : None,
    invoke   : Invoker,
    pools    : list[PoolStandIn],
    rom      : Path
) -> Path:
    """
    Takes a search of `brief` through `squirtl search` in `clone` on the
    fake game of `game`, in the process running the test.

    Returns:
        The run's directory, which the command prints.
    """
    return Path(invoke(["search", *brief]).output.strip())


@fixture
def found(
    accepted : None,
    brief    : list[str],
    clone    : Path,
    game     : None,
    invoke   : Invoker,
    pools    : list[PoolStandIn],
    rom      : Path
) -> Path:
    """
    Takes a search of `brief` through `squirtl search` in `clone` on the
    fake game of `game` until it reaches `EVENT_GOT_STARTER`, its steps
    raised to 100,000.

    Returns:
        The run's directory, which the command prints.
    """
    return Path(invoke(["search", *brief[:-2], "--steps", "100000"]).output.strip())


@fixture
def halted(
    accepted    : None,
    brief       : list[str],
    clone       : Path,
    game        : None,
    invoke      : Invoker,
    monkeypatch : MonkeyPatch,
    pools       : list[PoolStandIn],
    rom         : Path
) -> Path:
    """
    Takes a search of `brief` through `squirtl search` in `clone`, stopping
    it at the end of the first iteration reaching 20 presses, as `squirtl
    stop` would.

    Returns:
        The run's directory, which the command prints.
    """
    with monkeypatch.context() as patch:
        patch.setattr(
            Searcher,
            "stopping",
            property(lambda searcher: searcher.step >= 20)
        )

        return Path(invoke(["search", *brief]).output.strip())
