"""
Pins what `Results` reads from the run directories under
`docs/runs/`, covering:

- Each run's scores beside its baseline's, the comparison of each agent and
  curriculum across its runs, and random presses' share across every seed
- The curriculum's runs set against the same agent's runs from the bedroom
- A missing folder, which holds no run
- Every estimate holding whatever order the runs' names list in
- A run reading another cartridge than the default path, following a
  demonstration at an absolute path, or holding no evaluation of the agent
  or of the random baseline, which `Trained.read` refuses
"""

from collections.abc   import Callable, Iterable, Mapping
from common.evaluation import outcome, played
from datetime          import UTC, datetime
from pathlib           import Path
from pytest            import approx, raises

from squirtl.agent.schemas      import AgentSettings, Algorithm
from squirtl.docs.results       import Results, Trained
from squirtl.emulator.schemas   import EmulatorSettings
from squirtl.evaluation.schemas import Evaluation
from squirtl.runs.schemas       import CurriculumSettings, Revision, Run, RunSettings


def recorded(
    checkout : Callable[[Mapping[str, str]], None],
    rewards  : Iterable[float],
    second   : int,
    baseline : Iterable[float] = (0.125,),
    seed     : int | None      = None,
    settings : RunSettings     = RunSettings()
) -> Path:
    """
    Writes under `docs/runs/` a run started `second` seconds past midnight
    UTC on 4 October 2026 under the seed `seed`, or `second` where none is
    given, holding one evaluation per return in `rewards`, each a single
    episode reaching the starter where its return passes 0.5, beside a
    baseline of one episode per return in `baseline`, each reaching the
    starter where its return passes 0.5.
    """
    run = Run(
        digest   = "0",
        revision = Revision(commit="0", dirty=False, lockfile="0"),
        settings = settings.model_copy(
            update = {"seed": second if seed is None else seed}
        ),
        started = datetime(2026, 10, 4, 0, 0, second, tzinfo=UTC)
    )
    folder = f"docs/runs/{run.name}"
    checkout(
        {
            f"{folder}/baseline.json"     : Evaluation(
                outcomes = [
                    outcome(reward, terminated=reward > 0.5) for reward in baseline
                ],
                step = None
            ).model_dump_json(),
            f"{folder}/evaluations.jsonl" : "".join(
                played([reward], step, terminated=reward > 0.5).model_dump_json() + "\n"
                for step, reward in enumerate(rewards, start=1)
            ),
            f"{folder}/run.json"          : run.model_dump_json()
        }
    )

    return Path(folder)


def test_a_missing_folder_holds_no_run(checkout: Callable[[Mapping[str, str]], None]):
    """
    Asserts that results read from a checkout holding no `docs/runs/` hold
    no run, no comparison, and no share for random presses.
    """
    checkout({})

    assert Results.read() == Results(comparisons=(), random=None, runs=())


def test_a_run_following_a_demonstration_at_an_absolute_path_is_refused(
    checkout: Callable[[Mapping[str, str]], None]
):
    """
    Pins that a run whose curriculum followed a demonstration at an absolute
    path is refused, naming the path, so no local path reaches the site.
    """
    folder = recorded(
        checkout = checkout,
        rewards  = [0.75],
        second   = 1,
        settings = RunSettings(
            agent      = AgentSettings(algorithm=Algorithm.PPO),
            curriculum = CurriculumSettings(demonstration=Path("/home/demo"))
        )
    )

    with raises(ValueError, match="/home/demo"):
        Trained.read(folder)


def test_a_run_holding_no_baseline_is_refused(
    checkout: Callable[[Mapping[str, str]], None]
):
    """
    Pins that a run whose directory holds no baseline is refused, since each
    run is drawn beside its baseline.
    """
    folder = recorded(checkout, [0.75], 1)
    (folder / "baseline.json").rename(folder / "moved.json")

    with raises(ValueError, match="holds no baseline"):
        Trained.read(folder)


def test_a_run_holding_no_evaluation_is_refused(
    checkout: Callable[[Mapping[str, str]], None]
):
    """
    Pins that a run whose evaluations hold no line is refused, since the
    results draw each run from its evaluations.
    """
    folder = recorded(checkout, [], 1)

    with raises(ValueError, match="holds no evaluation"):
        Trained.read(folder)


def test_a_run_reading_another_cartridge_is_refused(
    checkout: Callable[[Mapping[str, str]], None]
):
    """
    Pins that a run trained against a cartridge other than the default path
    is refused, naming the path, so no local path reaches the site.
    """
    folder = recorded(
        checkout = checkout,
        rewards  = [0.75],
        second   = 1,
        settings = RunSettings(
            emulator = EmulatorSettings(cartridge=Path("/home/rom.gb"))
        )
    )

    with raises(ValueError, match="/home/rom.gb"):
        Trained.read(folder)


def test_comparisons_follow_the_agents_name_and_then_the_curriculum(
    checkout: Callable[[Mapping[str, str]], None]
):
    """
    Pins that the runs compare in one group for each agent and curriculum,
    in the order of the agent's name and then without the curriculum before
    with it, whatever order the runs' names take.
    """
    pqn = AgentSettings(algorithm=Algorithm.PQN)

    for second, settings in enumerate(
        (
            RunSettings(
                agent      = pqn,
                curriculum = CurriculumSettings(demonstration=Path("walk.json"))
            ),
            RunSettings(agent=AgentSettings(algorithm=Algorithm.PPO)),
            RunSettings(agent=pqn)
        ),
        start = 1
    ):
        recorded(
            checkout = checkout,
            rewards  = [0.75],
            second   = second,
            settings = settings
        )

    assert [
        (comparison.agent, comparison.curriculum)
        for comparison in Results.read().comparisons
    ] == [(Algorithm.PPO, False), (Algorithm.PQN, False), (Algorithm.PQN, True)]


def test_estimates_hold_whatever_order_the_runs_names_list_in(
    checkout: Callable[[Mapping[str, str]], None]
):
    """
    Pins that the same runs, written once under names listing in the order
    of their seeds and once in the reverse, read to the same comparisons and
    the same share for random presses, since each estimate orders its sample
    by seed before resampling it.
    """
    read = []

    for layout, order in (("first", 1), ("second", -1)):
        for seed in range(1, 7):
            recorded(
                baseline = [0.75] * seed + [0.25] * seed ** 2,
                checkout = checkout,
                rewards  = [seed / 7],
                second   = 30 + order * seed,
                seed     = seed
            )

        read.append(Results.read())
        Path("docs/runs").rename(f"docs/{layout}")

    first, second = read

    assert [run.seed for run in first.runs] == [1, 2, 3, 4, 5, 6]
    assert [run.seed for run in second.runs] == [6, 5, 4, 3, 2, 1]
    assert (first.comparisons, first.random) == (second.comparisons, second.random)


def test_random_presses_count_each_seed_once(
    checkout: Callable[[Mapping[str, str]], None]
):
    """
    Pins that random presses' share across the runs counts each seed's
    baseline once, however many agents trained under that seed.
    """
    ppo = RunSettings(agent=AgentSettings(algorithm=Algorithm.PPO))

    for seed in (1, 2, 3):
        recorded(checkout, [0.75], seed)
        recorded(
            checkout = checkout,
            rewards  = [0.75],
            second   = seed + 10,
            seed     = seed,
            settings = ppo
        )

    assert Results.read().random.runs == (3,)


def test_results_compare_each_agent_and_curriculum_across_its_runs(
    checkout: Callable[[Mapping[str, str]], None]
):
    """
    Pins that each run reaches the results as its scores beside its
    baseline's, in the order of its name, and that the runs of one agent
    compare against their baselines at each run's last evaluation, the
    agent's runs here reaching the starter every time and beating every
    baseline run.
    """
    for second in (1, 2, 3):
        recorded(checkout, [0.25, 0.75], second)

    results = Results.read()

    assert [
        (run.agent, run.curriculum, run.seed, [score.step for score in run.scores])
        for run in results.runs
    ] == [(Algorithm.DQN, False, second, [1, 2]) for second in (1, 2, 3)]
    assert [
        (
            comparison.agent, comparison.beats.value, comparison.baseline.value,
            comparison.reached.value, comparison.reached.runs
        )
        for comparison in results.comparisons
    ] == [(Algorithm.DQN, approx(1.0), approx(0.0), approx(1.0), (3,))]
    assert (results.random.value, results.random.runs) == (approx(0.0), (3,))


def test_the_curriculum_compares_against_the_same_agents_runs_from_the_bedroom(
    checkout: Callable[[Mapping[str, str]], None]
):
    """
    Pins that runs trained along the curriculum carry the probability that
    one beats a run of the same agent from the bedroom on mean return, here
    every curriculum run returning more, while runs from the bedroom and an
    agent trained along the curriculum alone carry none.
    """
    along = CurriculumSettings(demonstration=Path("walk.json"))
    pqn   = AgentSettings(algorithm=Algorithm.PQN)

    for second, reward, settings in (
        (1, 0.75, RunSettings(agent=pqn, curriculum=along)),
        (2, 0.75, RunSettings(agent=pqn, curriculum=along)),
        (3, 0.25, RunSettings(agent=pqn)),
        (4, 0.25, RunSettings(agent=pqn)),
        (
            5, 0.75,
            RunSettings(agent=AgentSettings(algorithm=Algorithm.PPO), curriculum=along)
        )
    ):
        recorded(
            checkout = checkout,
            rewards  = [reward],
            second   = second,
            settings = settings
        )

    assert [
        (
            comparison.agent, comparison.curriculum,
            None if comparison.bedroom is None else comparison.bedroom.value
        )
        for comparison in Results.read().comparisons
    ] == [
        (Algorithm.PPO, True, None),
        (Algorithm.PQN, False, None),
        (Algorithm.PQN, True, approx(1.0))
    ]
