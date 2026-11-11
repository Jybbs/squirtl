"""
Pins `Benchmark`, covering the evaluations it plays where its run lacks
them and reads where the run holds them, under the run's evaluation stream
and settings.
"""

from common.evaluation import EvaluatorStandIn, played
from datetime          import UTC, datetime
from pathlib           import Path
from pytest            import mark

from squirtl.agent.checkpoint      import Weights
from squirtl.agent.schemas         import AgentSettings
from squirtl.emulator.schemas      import Cartridge, EmulatorSettings
from squirtl.environment.overworld import Overworld
from squirtl.environment.schemas   import EnvironmentSettings
from squirtl.evaluation.schemas    import EvaluationSettings
from squirtl.reward.schemas        import RewardSettings
from squirtl.runs.benchmark        import Benchmark
from squirtl.runs.schemas          import Run, RunSettings, Stream


@mark.usefixtures("clone")
def test_a_benchmark_plays_the_evaluations_its_run_lacks_and_reads_those_it_holds(
    cartridge  : Cartridge,
    evaluators : list[EvaluatorStandIn]
):
    """
    Asserts that a run's first benchmark, at step 10, plays the agent and
    the baseline under the run's evaluation stream and settings and writes
    both into the run, that a second at step 10 reads both back without
    starting an evaluator, and that one at step 20 plays the agent alone,
    reading the baseline the run holds. The run's settings differ from each
    default, so the evaluator's arguments can only be the ones it recorded.
    """
    run = Run.start(
        "0",
        RunSettings(
            agent       = AgentSettings(device="meta"),
            emulator    = EmulatorSettings(cartridge=Path("rom.gb")),
            environment = EnvironmentSettings(max_episode_steps=6),
            evaluation  = EvaluationSettings(episodes=2),
            reward      = RewardSettings(goal=0.7, milestone=0.05),
            seed        = 7
        ),
        datetime(2026, 10, 4, tzinfo=UTC)
    )
    first, second, later = (
        Benchmark.from_run(cartridge, run, Weights(online={}, step=step))
        for step in (10, 10, 20)
    )

    assert [stand_in.asked for stand_in in evaluators] == [[10, None], [20]]
    assert evaluators[0].arguments == (
        run.settings.agent.algorithm, run.settings.agent.device,
        run.settings.seeds[Stream.EVALUATION],
        run.settings.evaluation,
        Overworld.specification(
            cartridge,
            run.settings.emulator,
            run.settings.environment,
            run.settings.reward
        )
    )
    assert (second, later.baseline) == (first, first.baseline)
    assert [evaluation.step for evaluation in run.evaluated] == [10, 20]


@mark.usefixtures("clone")
def test_a_run_holding_its_evaluation_but_no_baseline_plays_the_baseline_alone(
    cartridge  : Cartridge,
    evaluators : list[EvaluatorStandIn]
):
    """
    Asserts that a benchmark of a run holding the agent's evaluation at step
    10 but no baseline, as a resume from a run that wrote none leaves it,
    plays the baseline alone and writes it into the run.
    """
    run = Run.start("0", RunSettings(), datetime(2026, 10, 4, tzinfo=UTC))
    run.append(run.evaluations, played([0.01], 10))
    Benchmark.from_run(cartridge, run, Weights(online={}, step=10))

    assert ([stand_in.asked for stand_in in evaluators], run.baseline.exists()) == (
        [[None]],
        True
    )
