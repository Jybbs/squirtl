"""
Defines `evaluate`, the command that evaluates the agent of each run it
names against the random baseline across those runs and prints the figures.
"""

from collections.abc import Iterable
from cyclopts        import Parameter
from numpy.random    import default_rng
from typing          import Annotated

from squirtl.agent.checkpoint  import Weights
from squirtl.cli.logs          import listen, refusing
from squirtl.cli.runs          import ReleaseTag, RunDirectory, Selection
from squirtl.emulator.schemas  import Cartridge
from squirtl.evaluation.report import Pairs, Report
from squirtl.releases.schemas  import RunSelection
from squirtl.reward.schemas    import Event
from squirtl.runs.benchmark    import Benchmark
from squirtl.runs.schemas      import Run


def evaluate(
    directories : Annotated[
        list[RunDirectory] | None,
        Parameter(help="The directory of each run whose agent to evaluate.")
    ] = None,
    *,
    against     : Annotated[
        list[RunDirectory] | None,
        Parameter(
            help = (
                "The directory of each run of another agent to compare the first "
                "runs against."
            )
        )
    ] = None,
    release     : ReleaseTag = None,
    selector    : Selection  = None
):
    """
    Evaluates the agent of each run at its last checkpoint, over the
    episodes the run's settings record, beside the random baseline under the
    same seeds, and writes each evaluation into its run's directory, reading
    in place of playing any the run already holds. The deep Q-network and
    PQN play at the epsilon those settings record, and PPO takes its most
    likely action at every step.

    The runs are the ones the directories hold, or the runs `--release`
    attaches, each fetched into `data/runs/` where it is missing there.
    `--agent`, `--start`, and `--seed` select among the release's runs, and
    without them every seed of the recommended run's agent and start plays.

    Prints as Markdown each run's measures, then each measure's
    interquartile mean across the runs with its 95% percentile bootstrap
    interval and the count of runs behind it, then the probability that the
    agent beats its baseline, and the runs `--against` names where it names
    any, on each run's mean return.

    Both directories and `--release`, or neither, a directory holding no
    run, a release GitHub does not publish or one attaching no manifest, a
    selection matching none of its runs, a download whose digest differs or
    whose tar does not unpack, or runs ending their episodes at more than
    one goal, whose shares reaching it do not compare, exits 1 before any
    evaluation. A run holding no checkpoint, holding a damaged one, reading
    a cartridge the emulator refuses, or recording another digest than the
    state its intro leaves on the cartridge exits 1, keeping the evaluations
    already written for the runs evaluated before it.
    """
    listen()

    with refusing(OSError, ValueError):
        runs = RunSelection(
            directories = directories or (),
            release     = release,
            selector    = selector
        ).every()
        rivals = [Run.read(directory) for directory in against or ()]
        Event.check_shared(
            (run.settings.environment.goal for run in (*runs, *rivals)),
            "the runs named"
        )

    print(
        Report(against=evaluated(rivals), runs=evaluated(runs)).markdown(
            default_rng([run.settings.seed for run in runs])
        )
    )


def evaluated(runs: Iterable[Run]) -> Pairs:
    """
    Evaluates the agent of each of `runs` at its last checkpoint beside the
    random baseline, unless the run holds both already, exiting 1 on a run
    holding no checkpoint, holding a damaged one, reading a cartridge the
    emulator refuses, or recording another digest than the state its intro
    leaves.

    Returns:
        The agent's evaluation and the baseline's under each run's name.
    """
    pairs = {}

    for run in runs:
        with refusing(OSError, ValueError):
            weights   = Weights.from_path(run.checkpoint)
            cartridge = Cartridge.read(run.settings.emulator.cartridge)
            benchmark = Benchmark.from_run(cartridge, run, weights)

        pairs[run.name] = benchmark.agent, benchmark.baseline

    return pairs
