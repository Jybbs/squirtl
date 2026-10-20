"""
Defines `evaluate`, the command that evaluates the agent of each run it
names against the random baseline across those runs and prints the figures.
"""

from collections.abc import Iterable
from cyclopts        import Parameter
from numpy.random    import default_rng
from pathlib         import Path
from typing          import Annotated

from squirtl.agent.schemas     import Weights
from squirtl.cli.logs          import listen, refusing
from squirtl.emulator.schemas  import Cartridge
from squirtl.evaluation.report import Pairs, Report
from squirtl.runs.schemas      import Run


def evaluate(
    directories : Annotated[
        list[Path],
        Parameter(
            help = "The directory of each run whose agent to evaluate."
        )
    ],
    *,
    against     : Annotated[
        list[Path] | None,
        Parameter(
            help = (
                "The directory of each run of another agent to compare the first "
                "runs against."
            )
        )
    ] = None
):
    """
    Evaluates the agent of each run at its last checkpoint, at the epsilon
    and over the episodes the run's settings record, beside the random
    baseline under the same seeds, and writes each evaluation into its run's
    directory, reading in place of playing any the run already holds.

    Prints as Markdown each run's measures, then each measure's
    interquartile mean across the runs with its 95% percentile bootstrap
    interval and the count of runs behind it, then the probability that the
    agent beats its baseline, and the runs `--against` names where it names
    any, on each run's mean return.

    A directory holding no run exits 1 before any evaluation, and a run
    holding no checkpoint or reading a cartridge the emulator refuses exits
    1, keeping the evaluations already written for the runs evaluated before
    it.
    """
    listen()

    with refusing(OSError, ValueError):
        runs, rivals = (
            [Run.read(directory) for directory in group]
            for group in (directories, against or [])
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
    holding no checkpoint or reading a cartridge the emulator refuses.

    Returns:
        The agent's evaluation and the baseline's under each run's name.
    """
    pairs = {}

    for run in runs:
        with refusing(OSError, ValueError):
            weights   = Weights.from_path(run.checkpoint)
            cartridge = Cartridge.read(run.settings.emulator.cartridge)

        pairs[run.name] = run.evaluate(cartridge, weights)

    return pairs
