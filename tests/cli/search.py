"""
Pins what `squirtl search` does, covering:

- A search taken through to its end, which logs a line per iteration, prints
  its directory, and exits zero with its record, its iterations, its path,
  and its checkpoint in that directory
- The settings it reads, from a flag and from the `[tool.squirtl]` table,
  and a setting only training reads exiting 2
- A `--resume` continuing in a new directory under the recorded settings
- A `--resume` directory it cannot continue, a cartridge the emulator refuses,
  and a working directory no clone holds, each exiting 1 before making any
  directory
- `squirtl stop` ending a search at its iteration's end, a second interrupt
  exiting 130, `squirtl train --resume` and `squirtl evaluate` naming what
  reads a search, and each worker process coming down with the command
"""

from collections.abc import Callable, Mapping
from common.cli      import Invoker
from common.search   import PoolStandIn, iterations, lines
from pathlib         import Path
from pytest          import MonkeyPatch, mark, param
from signal          import SIGINT, raise_signal

from squirtl.runs.schemas  import Run
from squirtl.runs.searcher import Searcher


def damaged(run: Run):
    """
    Cuts the checkpoint of `run` in half.
    """
    data = run.checkpoint.read_bytes()

    run.checkpoint.write_bytes(data[:len(data) // 2])


def short_of_it(run: Run):
    """
    Empties the iterations of `run`.
    """
    run.iterations.write_text("", "utf-8")


@mark.usefixtures("accepted", "clone", "game", "pools", "rom")
def test_a_search_exits_zero_and_logs_a_line_per_iteration(
    brief  : list[str],
    invoke : Invoker
):
    """
    Asserts that the command exits zero, printing the directory alone on
    standard output, and logs one line per iteration naming its reward and
    its positions.
    """
    invocation = invoke(["search", *brief])
    logged     = [line for line in invocation.messages if line.startswith("Iteration")]

    assert (invocation.code, len(logged)) == (
        0,
        len(lines(Run.read(Path(invocation.output.strip()))))
    )
    assert "reached a reward of" in logged[0] and "positions at press" in logged[0]


@mark.usefixtures("accepted", "clone", "game", "pools", "rom")
def test_a_search_reads_each_setting_from_its_flag_and_the_table(
    brief    : list[str],
    checkout : Callable[[Mapping[str, str]], None],
    invoke   : Invoker
):
    """
    Asserts that a run records a setting the `[tool.squirtl]` table of the
    manifest names, and one its flag names over that table, as `squirtl
    train` reads them.
    """
    checkout({"pyproject.toml": "[tool.squirtl]\nseed = 7\n"})

    tabled  = Path(invoke(["search", *brief]).output.strip())
    flagged = Path(invoke(["search", *brief, "--seed", "9"]).output.strip())

    assert (Run.read(tabled).settings.seed, Run.read(flagged).settings.seed) == (7, 9)


def test_a_finished_search_holds_an_iteration_reaching_its_steps(searched: Path):
    """
    Asserts that the last iteration a search records reaches the steps it
    was given or the starter.
    """
    settings = Run.read(searched).settings
    last     = iterations(Run.read(searched))[-1]

    assert last.presses >= settings.steps or last.reward >= settings.reward.starter


def test_a_resume_continues_in_a_new_directory_under_the_recorded_settings(
    halted   : Path,
    invoke   : Invoker,
    searched : Path
):
    """
    Asserts that resuming a stopped search exits zero with a new directory
    recording the search it resumes, under that search's settings whatever
    the flags name, and ends on the lines of a search that never stopped.
    """
    invocation = invoke(["search", "--resume", str(halted)])
    resumed    = Run.read(Path(invocation.output.strip()))

    assert (invocation.code, resumed.resumes, resumed.settings) == (
        0, halted.name,
        Run.read(halted).settings
    )
    assert lines(resumed) == lines(Run.read(searched))


@mark.parametrize(
    ("damage", "logged"),
    [
        param(damaged, "checkpoint.npz", id="a-damaged-checkpoint"),
        param(short_of_it, "holds 0 lines", id="iterations-short-of-it"),
        param(lambda run: run.checkpoint.unlink(), "checkpoint.npz", id="no-checkpoint")
    ]
)
def test_a_resume_it_cannot_continue_exits_1_before_making_any_directory(
    damage : Callable[[Run], None],
    halted : Path,
    invoke : Invoker,
    logged : str
):
    """
    Asserts that resuming from a damaged or a missing checkpoint, or one
    the iterations end short of, exits 1 logging one line naming the fault
    in place of a traceback, and makes no directory beside the stopped
    search's.
    """
    damage(Run.read(halted))
    invocation = invoke(["search", "--resume", str(halted)])

    assert (invocation.code, len(invocation.messages), logged in invocation.log) == (
        1, 1, True
    )
    assert [*Path("data/runs").iterdir()] == [halted]


def test_a_resume_of_a_finished_search_exits_1_before_making_any_directory(
    invoke   : Invoker,
    searched : Path
):
    """
    Asserts that resuming a search whose checkpoint already holds its end
    exits 1 saying so, and makes no directory beside that search's.
    """
    invocation = invoke(["search", "--resume", str(searched)])

    assert (invocation.code, "already holds the search's end" in invocation.log) == (
        1, True
    )
    assert [*Path("data/runs").iterdir()] == [searched]


def test_a_resume_of_a_training_run_exits_1_naming_its_command(
    invoke  : Invoker,
    trained : Path
):
    """
    Asserts that resuming a training run through `squirtl search` exits 1,
    naming the command that continues one.
    """
    invocation = invoke(["search", "--resume", str(trained)])

    assert (invocation.code, "squirtl train" in invocation.log) == (1, True)
    assert [*Path("data/runs").iterdir()] == [trained]


@mark.parametrize(
    "flag",
    [
        param("--curriculum.window", id="curriculum"),
        param("--evaluation.episodes", id="evaluation"),
        param("--evaluation-steps", id="evaluation-steps")
    ]
)
@mark.usefixtures("clone")
def test_a_training_setting_exits_2_before_making_any_directory(
    flag   : str,
    invoke : Invoker
):
    """
    Asserts that `squirtl search` refuses each setting only training reads
    as an option it does not know, exiting 2 as cyclopts does on a token it
    cannot parse, before any directory is made.
    """
    invocation = invoke(["search", flag, "3"])

    assert (
        invocation.code,
        f"Unknown option: {flag}" in invocation.log,
        Path("data/runs").exists()
    ) == (2, True, False)


@mark.usefixtures("clone")
def test_a_resume_directory_holding_no_run_exits_1(invoke: Invoker, tmp_path: Path):
    """
    Asserts that a `--resume` directory holding no run exits 1 and makes no
    directory under `data/runs/`.
    """
    invocation = invoke(["search", "--resume", str(tmp_path / "nothing")])

    assert (invocation.code, Path("data/runs").exists()) == (1, False)


@mark.usefixtures("clone", "rom")
def test_a_cartridge_the_emulator_refuses_exits_1_before_making_any_directory(
    brief  : list[str],
    invoke : Invoker
):
    """
    Asserts that a cartridge whose digest pret/pokered lists under no
    edition exits 1 and makes no directory.
    """
    assert (invoke(["search", *brief]).code, Path("data/runs").exists()) == (1, False)


@mark.usefixtures("accepted", "outside", "rom")
def test_a_working_directory_no_clone_holds_exits_1_before_making_any_directory(
    brief  : list[str],
    invoke : Invoker
):
    """
    Asserts that a search started where no git clone holds the working
    directory exits 1, since a run records the revision it ran on.
    """
    assert (invoke(["search", *brief]).code, Path("data/runs").exists()) == (1, False)


@mark.usefixtures("searched")
def test_a_search_shuts_down_the_workers_it_booted(pools: list[PoolStandIn]):
    """
    Asserts that the command leaves no worker running behind it, shutting
    down the pool and dropping each rollout not yet started.
    """
    assert pools[0].shutdowns == [True]


@mark.usefixtures("accepted", "clone", "game", "pools", "rom")
def test_a_second_interrupt_exits_130(
    brief       : list[str],
    invoke      : Invoker,
    monkeypatch : MonkeyPatch
):
    """
    Asserts that a second interrupt ends the search at once, exiting with
    the status a shell reports for an interrupted command.
    """
    iterate = Searcher.__iter__

    def twice(searcher: Searcher):
        """
        Raises the signal twice over before the loop's first outer step.
        """
        raise_signal(SIGINT)
        raise_signal(SIGINT)

        yield from iterate(searcher)

    monkeypatch.setattr(Searcher, "__iter__", twice)

    assert invoke(["search", *brief]).code == 130


def test_a_search_reaching_its_goal_writes_the_path_as_its_one_episode(found: Path):
    """
    Asserts that a search reaching its goal writes the path it found as the
    one episode of its directory, reaching that goal from Blue's bedroom, so
    a curriculum takes the directory as its demonstration.
    """
    run = Run.read(found)

    assert [len(run.demonstration.presses)] == [
        episode.length for episode in run.recorded
    ]


def test_a_search_writes_its_run_and_prints_its_directory(searched: Path):
    """
    Asserts that a search stopping short of its goal leaves a run recording
    itself as a search, its iterations, its checkpoint, and no episode, in
    the one directory the command prints.
    """
    run = Run.read(searched)

    assert (
        run.searches,
        run.iterations.exists(),
        run.checkpoint.exists(),
        [*run.recorded]
    ) == (True, True, True, [])
    assert [*Path("data/runs").iterdir()] == [searched]


def test_a_stop_of_a_search_writes_its_stop_file(invoke: Invoker, searched: Path):
    """
    Asserts that `squirtl stop` on a search exits zero having written the
    search's stop file.
    """
    invocation = invoke(["stop", str(searched)])

    assert (invocation.code, Run.read(searched).stop.exists()) == (0, True)
