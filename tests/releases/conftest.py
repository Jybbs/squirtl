"""
Defines the fixtures the tests of `squirtl.releases` request:

- `recorded`, a factory of runs written under `data/runs/` and listed under
  `docs/runs/` as a checkout commits them
- `committed`, three such runs, one following a demonstration, beside the
  demonstration itself
- `packed`, the manifest `ReleaseManifest.pack` writes for them
- `published`, the release `github` publishes attaching every file of
  `packed`
"""

from collections.abc import Callable, Mapping
from common.releases import GitHub
from datetime        import UTC, datetime
from numpy           import zeros
from pathlib         import Path
from pytest          import fixture
from torch           import tensor

from squirtl.agent.checkpoint    import ReplayCheckpoint
from squirtl.agent.schemas       import AgentSettings, Algorithm
from squirtl.docs.results        import ReleaseSettings
from squirtl.emulator.schemas    import EmulatorSettings
from squirtl.environment.schemas import Recording
from squirtl.releases.schemas    import ReleaseManifest
from squirtl.reward.schemas      import Term
from squirtl.runs.schemas        import Episode, Revision, Run
from squirtl.runs.settings       import CurriculumSettings, RunSettings

type Recorder = Callable[..., Run]


@fixture
def recorded(checkout: Callable[[Mapping[str, str]], None]) -> Recorder:
    """
    Builds a writer of a run started `second` seconds past midnight UTC
    on 8 November 2026, on the cartridge and under the demonstration a
    pod's absolute paths name, into `data/runs/`, holding one episode, a
    checkpoint holding replay memory, an evaluation, and a baseline, and
    lists it under `docs/runs/` where `listed` is set. Where `searches` is
    set, the run is a search, holding no checkpoint.
    """
    checkout({})

    def record(
        second        : int,
        algorithm     : Algorithm  = Algorithm.PPO,
        demonstration : str | None = None,
        listed        : bool       = True,
        searches      : bool       = False,
        seed          : int        = 1
    ) -> Run:
        """
        Writes the run and returns it, read back from its directory.
        """
        run = Run(
            digest   = "0",
            revision = Revision(commit="0", dirty=False, lockfile="0"),
            settings = RunSettings(
                agent      = AgentSettings(algorithm=algorithm),
                curriculum = CurriculumSettings(
                    demonstration = demonstration and Path("/root/demo", demonstration)
                ),
                emulator = EmulatorSettings(cartridge=Path("/root/rom/PokemonBlue.gb")),
                seed     = seed
            ),
            searches = searches,
            started  = datetime(2026, 11, 8, 0, 0, second, tzinfo=UTC)
        )
        run.directory.mkdir(parents=True)
        run.record.write_text(run.model_dump_json(indent=2), encoding="utf-8")
        run.append(
            run.episodes,
            Episode(
                epsilon    = None,
                length     = 3,
                positions  = 3,
                recording  = Recording(presses=bytes([1, 4, 4]), timer_div=9),
                reward     = 0.125,
                seconds    = 0.5,
                shares     = dict.fromkeys(Term, 0.0) | {Term.NOVELTY: 0.125},
                terminated = False,
                update     = None
            )
        )
        run.evaluations.write_text("{}\n", encoding="utf-8")
        run.baseline.write_text("{}", encoding="utf-8")

        if not searches:
            ReplayCheckpoint(
                exploration = {},
                online      = {"weight": tensor([1.0, 2.0])},
                optimizer   = {"state": {}},
                replay      = {"frames": zeros((2, 4), "uint8")},
                sampling    = {},
                step        = 8,
                target      = {"weight": tensor([1.0, 2.0])}
            ).save(run.checkpoint)

        if listed:
            Path("docs/runs", run.name).mkdir(parents=True)

        return Run.read(run.directory)

    return record


@fixture
def committed(recorded: Recorder) -> list[Run]:
    """
    Writes the runs of PPO from the bedroom and along the curriculum under
    seed 1 and of the deep Q-network under seed 2, then the demonstration
    the curriculum's run follows, which `docs/runs/` leaves out.

    Returns:
        The three listed runs, then the demonstration.
    """
    trained = [
        recorded(1),
        recorded(2, demonstration="20261108T000009.000000Z"),
        recorded(3, algorithm=Algorithm.DQN, seed=2)
    ]

    return [*trained, recorded(9, listed=False, seed=6)]


@fixture
def packed(committed: list[Run]) -> ReleaseManifest:
    """
    Packs `committed` into `dist/runs/`, recommending the run of PPO from
    the bedroom.
    """
    return ReleaseManifest.pack(ReleaseSettings(recommended_run=committed[0].name))


@fixture
def published(github: GitHub, packed: ReleaseManifest) -> GitHub:
    """
    Publishes the release `0.2.0` attaching every file `packed` lists.
    """
    github.publish(packed)

    return github
