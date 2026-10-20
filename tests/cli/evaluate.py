"""
Pins what `squirtl evaluate` does, covering:

- The evaluations it writes into a run's directory, played across worker
  processes, and the report it prints from them
- The evaluations a run already holds, which it reads in place of playing
- The runs `--against` names, which it compares the first runs with
- A directory holding no run, a run missing its checkpoint or its
  cartridge, and a damaged checkpoint, each exiting 1, and a damaged
  member of replay memory, which it never reads
"""

from collections.abc   import Callable
from common.cli        import Invoker
from common.evaluation import EvaluatorStandIn
from os                import truncate
from pathlib           import Path
from pytest            import mark, param
from zipfile           import ZipFile

from squirtl.runs.schemas import Run


def test_a_directory_holding_no_run_exits_1_before_any_evaluation(
    clone      : Path,
    evaluators : list[EvaluatorStandIn],
    invoke     : Invoker
):
    """
    Asserts that evaluating a directory holding no run record exits 1 and
    starts no evaluator.
    """
    (clone / "data/runs/empty").mkdir(parents=True)

    assert (invoke(["evaluate", "data/runs/empty"]).code, evaluators) == (1, [])


@mark.parametrize(
    "missing",
    [
        param(lambda run: run.checkpoint,                  id="the-checkpoint"),
        param(lambda run: run.settings.emulator.cartridge, id="the-cartridge")
    ]
)
def test_a_run_missing_its_checkpoint_or_its_cartridge_exits_1_naming_the_file(
    evaluators : list[EvaluatorStandIn],
    invoke     : Invoker,
    missing    : Callable[[Run], Path],
    trained    : Path
):
    """
    Asserts that evaluating a run whose checkpoint or whose cartridge is
    gone exits 1, naming the file it lacks, and starts no evaluator.
    """
    path = missing(Run.read(trained))
    path.unlink()
    invocation = invoke(["evaluate", str(trained)])

    assert (invocation.code, path.name in invocation.log, evaluators) == (1, True, [])


@mark.usefixtures("evaluators")
def test_runs_against_another_agent_take_a_column_and_a_comparison(
    invoke  : Invoker,
    quick   : list[str],
    trained : Path
):
    """
    Asserts that naming a second run through `--against` adds its column to
    the table across the runs and a sentence giving the probability that the
    agent beats it.
    """
    rival  = invoke(["train", *quick, "--seed", "2"]).output.strip()
    output = invoke(["evaluate", str(trained), "--against", rival]).output

    assert "| **Measure** | **Agent** | **Baseline** | **Against** |" in output
    assert "The agent beats the runs against it with a probability of" in output


def test_a_run_holding_a_damaged_checkpoint_exits_1_naming_it(
    evaluators : list[EvaluatorStandIn],
    invoke     : Invoker,
    trained    : Path
):
    """
    Asserts that evaluating a run whose checkpoint holds its first half
    alone exits 1, logging that the file holds no whole checkpoint, and
    starts no evaluator.
    """
    checkpoint = Run.read(trained).checkpoint
    truncate(checkpoint, checkpoint.stat().st_size // 2)
    invocation = invoke(["evaluate", str(trained)])

    assert (
        invocation.code,
        "holds no whole checkpoint" in invocation.log,
        evaluators
    ) == (
        1, True,
        []
    )


def test_a_second_evaluation_reads_what_the_first_wrote(
    evaluators : list[EvaluatorStandIn],
    invoke     : Invoker,
    trained    : Path
):
    """
    Asserts that evaluating a run a second time starts no evaluator, reading
    the evaluation and the baseline the first wrote, and prints the same
    report.
    """
    first, second = (invoke(["evaluate", str(trained)]) for _ in range(2))

    assert (len(evaluators), second.output) == (1, first.output)


def test_an_evaluation_reads_the_agent_member_of_the_checkpoint_alone(
    invoke  : Invoker,
    trained : Path
):
    """
    Asserts that evaluating a run whose checkpoint holds a damaged member
    of replay memory beside a whole `agent.pt` exits zero, since the command
    reads `agent.pt` alone.
    """
    checkpoint = Run.read(trained).checkpoint

    with ZipFile(checkpoint) as archive:
        agent = archive.read("agent.pt")

    with ZipFile(checkpoint, "w") as archive:
        archive.writestr("agent.pt", agent)
        archive.writestr("actions.npy", b"\x93NUMPY\x01\x00")

    assert invoke(["evaluate", str(trained)]).code == 0


def test_an_evaluation_writes_its_episodes_and_prints_the_report(
    invoke  : Invoker,
    trained : Path
):
    """
    Asserts that evaluating a run at its checkpoint on step 10 exits zero,
    writes the agent's evaluation of two episodes and the baseline's into
    its directory, and prints the table of each run, the table across the
    runs, and the agent's probability of beating its baseline, a tie on the
    blank cartridge's returns of 0 counting half.
    """
    invocation = invoke(["evaluate", str(trained)])
    run        = Run.read(trained)

    assert (invocation.code, run.baseline.exists()) == (0, True)
    assert [(
        evaluation.step,
        len(evaluation.outcomes)
    ) for evaluation in run.evaluated] == [(10, 2)]
    assert [part.split(" | ")[0] for part in invocation.output.split("\n\n")] == [
        "| **Run**",
        "| **Measure**",
        "The agent beats its baseline with a probability of 0.5 over 1 and 1 runs, "
        "on each run's mean return.\n"
    ]
