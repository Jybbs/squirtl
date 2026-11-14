"""
Pins what `squirtl train` does, covering:

- The run it writes under `data/runs/` and the directory it prints
- The cartridge, the `--resume` directory, and the working directory outside
  a clone it refuses before making any directory, among them a run holding
  no checkpoint or one already holding its steps, a damaged checkpoint, a
  log short of its checkpoint, replay memory of another shape, a
  demonstration directory holding no run, and a search
- A search's setting, which it takes no flag for
- A resume into a new directory under the settings the stopped run recorded
- The line each episode logs and the line each step logs under `--verbose`
- The emulator's window `--emulator.open-window` opens
- PQN's and PPO's run across environments and a resume of one stopped short
"""

from collections.abc import Callable
from common.cli      import Invoker
from os              import truncate
from pathlib         import Path
from pytest          import MonkeyPatch, mark, param

from squirtl.agent.checkpoint import ReplayCheckpoint
from squirtl.runs.handover    import VectorCheckpoint
from squirtl.runs.schemas     import Run
from squirtl.runs.trainer     import Trainer


def cut_checkpoint(run: Run):
    """
    Cuts the checkpoint of `run` to its first half, as a write the machine
    lost power during leaves it.
    """
    truncate(run.checkpoint, run.checkpoint.stat().st_size // 2)


@mark.usefixtures("clone")
def test_a_missing_cartridge_exits_1_before_making_any_directory(
    invoke : Invoker,
    quick  : list[str]
):
    """
    Asserts that a run reading a cartridge path no file sits at exits 1,
    logging that path, before making any directory under `data/`.
    """
    invocation = invoke(["train", *quick])

    assert (invocation.code, "data/rom.gb" in invocation.log) == (1, True)
    assert not Path("data").exists()


@mark.usefixtures("clone", "rom")
def test_a_cartridge_the_emulator_refuses_exits_1_before_making_any_directory(
    invoke : Invoker,
    quick  : list[str]
):
    """
    Asserts that a run reading a cartridge whose digest names no release
    `Edition` lists exits 1, logging the refusal its validator raised as one
    line with none of Pydantic's own text around it, and makes no directory
    under `data/runs/`.
    """
    invocation = invoke(["train", *quick])

    assert (
        invocation.code,
        len(invocation.messages),
        invocation.messages[0].startswith(
            "data/rom.gb is not the English Pokémon Blue ROM"
        )
    ) == (1, 1, True)
    assert not Path("data/runs").exists()


def drop_last_episode(run: Run):
    """
    Drops the line of the last episode `run` recorded, as a crash that lost
    the log's last write leaves it.
    """
    lines = run.episodes.read_text(encoding="utf-8").splitlines(True)
    run.episodes.write_text("".join(lines[:-1]), encoding="utf-8")


def reshape_flags(run: Run):
    """
    Rewrites the checkpoint of `run` with replay memory holding `flags` cut
    to one slot.
    """
    checkpoint = ReplayCheckpoint.from_path(run.checkpoint)
    checkpoint.model_copy(
        update = {
            "replay": checkpoint.replay | {"flags": checkpoint.replay["flags"][:1]}
        }
    ).save(run.checkpoint)


def test_a_resume_continues_in_a_new_directory_under_the_recorded_settings(
    invoke  : Invoker,
    stopped : Path
):
    """
    Asserts that resuming a run stopped on step 8 writes a new directory
    naming the run it continues, under the settings and the digest that
    run recorded whatever the flags set, holding that run's lines and a
    checkpoint of its own at the run's tenth and last step.
    """
    invocation = invoke(["train", "--resume", str(stopped), "--steps", "99"])
    resumed    = Run.read(Path(invocation.output.strip()))
    previous   = Run.read(stopped)

    assert (invocation.code, resumed.resumes, resumed.settings, resumed.digest) == (
        0, stopped.name, previous.settings, previous.digest
    )
    assert (
        resumed.episodes.read_text(encoding="utf-8"),
        ReplayCheckpoint.from_path(resumed.checkpoint).step
    ) == (previous.episodes.read_text(encoding="utf-8"), 10)


@mark.parametrize(
    ("damage", "logged"),
    [
        param(
            cut_checkpoint,
            "holds no whole checkpoint",
            id = "a-damaged-checkpoint"
        ),
        param(
            drop_last_episode,
            "short of the checkpoint at step 8",
            id = "a-log-short-of-it"
        ),
        param(
            reshape_flags,
            "replay memory holds `flags` as uint8 at the shape (64, 1), where the "
            "arrays loaded hold uint8 at (1, 1)",
            id = "replay-memory-of-another-shape"
        )
    ]
)
def test_a_resume_it_cannot_continue_exits_1_on_one_line_before_making_any_directory(
    damage  : Callable[[Run], None],
    invoke  : Invoker,
    logged  : str,
    stopped : Path
):
    """
    Asserts that resuming from a damaged checkpoint, a checkpoint the log
    ends short of, or replay memory of another shape than the recorded
    settings give exits 1, logging one line naming the fault in place of a
    traceback, and makes no directory beside the stopped run's.
    """
    damage(Run.read(stopped))
    invocation = invoke(["train", "--resume", str(stopped)])

    assert (invocation.code, len(invocation.messages), logged in invocation.log) == (
        1, 1, True
    )
    assert list(Path("data/runs").iterdir()) == [stopped]


def test_a_resume_of_a_finished_run_exits_1_before_making_any_directory(
    invoke  : Invoker,
    trained : Path
):
    """
    Asserts that resuming a run whose checkpoint already holds its ten steps
    exits 1 saying so, and makes no directory beside that run's.
    """
    invocation = invoke(["train", "--resume", str(trained)])

    assert (invocation.code, "already holds the run's 10 steps" in invocation.log) == (
        1, True
    )
    assert list(Path("data/runs").iterdir()) == [trained]


def test_a_resume_of_a_run_holding_no_checkpoint_exits_1_before_making_any_directory(
    invoke  : Invoker,
    trained : Path
):
    """
    Asserts that resuming a run that holds no checkpoint, as one ended at
    once before its first leaves it, exits 1 naming the missing file and
    makes no directory beside that run's.
    """
    Run.read(trained).checkpoint.unlink()
    invocation = invoke(["train", "--resume", str(trained)])

    assert (invocation.code, "checkpoint.npz" in invocation.log) == (1, True)
    assert list(Path("data/runs").iterdir()) == [trained]


@mark.usefixtures("accepted", "outside", "rom")
def test_a_working_directory_no_clone_holds_exits_1_before_making_any_directory(
    invoke : Invoker,
    quick  : list[str]
):
    """
    Asserts that a run started where no git clone holds the working
    directory exits 1, logging the `git` command that failed in place of a
    traceback, and makes no directory there.
    """
    invocation = invoke(["train", *quick])

    assert (invocation.code, "git', 'rev-parse', 'HEAD'" in invocation.log) == (1, True)
    assert not Path("data/runs").exists()


@mark.usefixtures("clone")
def test_a_resume_directory_holding_no_run_exits_1_before_making_any_directory(
    invoke: Invoker
):
    """
    Asserts that resuming from a directory holding no run record exits 1 and
    makes no directory under `data/runs/`.
    """
    Path("data/runs/empty").mkdir(parents=True)

    assert invoke(["train", "--resume", "data/runs/empty"]).code == 1
    assert [path.name for path in Path("data/runs").iterdir()] == ["empty"]


@mark.parametrize(("flags", "logged"), [([], 0), (["--verbose"], 10)])
@mark.usefixtures("accepted", "clone", "rom")
def test_each_episode_logs_a_line_and_each_step_one_under_verbose(
    flags  : list[str],
    invoke : Invoker,
    logged : int,
    quick  : list[str]
):
    """
    Asserts that a run logs a line for each of its two episodes, and under
    `--verbose` a line for each of its ten steps beside them, above the
    progress bar at its last step.
    """
    log = invoke(["train", *quick, *flags]).log

    assert (log.count("Episode "), log.count("Step "), "━ 100% " in log) == (
        2, logged, True
    )


@mark.usefixtures("clone")
def test_a_search_setting_exits_2_before_making_any_directory(invoke: Invoker):
    """
    Asserts that `squirtl train` refuses `--search.particles` as an option
    it does not know, exiting 2 as cyclopts does on a token it cannot parse,
    before any directory is made.
    """
    invocation = invoke(["train", "--search.particles", "3"])

    assert (
        invocation.code,
        "Unknown option: --search.particles" in invocation.log,
        Path("data/runs").exists()
    ) == (2, True, False)


def test_a_resume_of_a_search_exits_1_naming_the_commands_reading_one(
    invoke   : Invoker,
    searched : Path
):
    """
    Asserts that resuming a search through `squirtl train` exits 1 naming
    `squirtl watch` and `squirtl search --resume`, and makes no directory
    beside the search's.
    """
    invocation = invoke(["train", "--resume", str(searched)])

    assert (
        invocation.code,
        "squirtl watch" in invocation.log,
        "squirtl search --resume" in invocation.log,
        list(Path("data/runs").iterdir())
    ) == (1, True, True, [searched])


@mark.parametrize(
    ("flags", "window"),
    [
        param([],                         "null", id="headless-by-default"),
        param(["--emulator.open-window"], "SDL2", id="the-window-flag")
    ]
)
@mark.usefixtures("accepted", "clone", "rom")
def test_the_window_flag_boots_the_emulator_in_its_sdl2_window(
    flags   : list[str],
    invoke  : Invoker,
    quick   : list[str],
    window  : str,
    windows : list[str]
):
    """
    Asserts that a run boots the emulator with no window by default and in
    its SDL2 window under `--emulator.open-window`.
    """
    invoke(["train", *quick, *flags])

    assert windows == [window]


def test_a_run_of_pqn_or_ppo_writes_its_lines_and_its_checkpoint(rolled: Path):
    """
    Asserts that either agent's run across two environments exits
    zero having written, in the directory it prints, a line for each
    environment's two 3-step episodes and its checkpoint at its sixteenth
    and last step.
    """
    run = Run.read(rolled)

    assert (
        len(list(run.recorded)),
        VectorCheckpoint.from_path(run.checkpoint).step
    ) == (4, 16)


def test_a_run_writes_its_record_lines_and_checkpoint_and_prints_its_directory(
    trained: Path
):
    """
    Asserts that a run exits zero having written, in the directory under
    `data/runs/` it prints, its record, a line for each of its two 4-step
    episodes, and its checkpoint at its tenth and last step.
    """
    run = Run.read(trained)

    assert (
        trained.parent,
        len(list(run.recorded)),
        ReplayCheckpoint.from_path(run.checkpoint).step
    ) == (Path("data/runs"), 2, 10)


@mark.parametrize("algorithm", [param("ppo", id="ppo"), param("pqn", id="pqn")])
@mark.usefixtures("accepted", "clone", "rom")
def test_a_stopped_run_of_pqn_or_ppo_resumes_in_a_new_directory(
    algorithm   : str,
    invoke      : Invoker,
    monkeypatch : MonkeyPatch,
    rolling     : Callable[[str], list[str]]
):
    """
    Asserts that resuming a run of either agent stopped at step 8 writes a
    new directory naming that run, under the settings it recorded, holding
    the lines it wrote and those of the steps left, its checkpoint at the
    sixteenth and last step.
    """
    with monkeypatch.context() as patch:
        patch.setattr(
            Trainer,
            "stopping",
            property(lambda trainer: trainer.agent.step >= 8)
        )
        stopped = Run.read(Path(invoke(["train", *rolling(algorithm)]).output.strip()))

    invocation = invoke(["train", "--resume", str(stopped.directory)])
    resumed    = Run.read(Path(invocation.output.strip()))

    assert (invocation.code, resumed.resumes, resumed.settings) == (
        0, stopped.name, stopped.settings
    )
    assert (
        len(list(stopped.recorded)),
        len(list(resumed.recorded)),
        VectorCheckpoint.from_path(resumed.checkpoint).step
    ) == (2, 4, 16)


@mark.usefixtures("accepted", "clone", "rom")
def test_a_demonstration_directory_holding_no_run_exits_1_before_making_any_directory(
    invoke  : Invoker,
    rolling : Callable[[str], list[str]]
):
    """
    Asserts that a run of PPO along a directory holding no run exits
    1, logging that directory's record, and makes no directory under
    `data/runs/`.
    """
    invocation = invoke(
        ["train", *rolling("ppo"), "--curriculum.demonstration", "data/runs/none"]
    )

    assert (invocation.code, "data/runs/none/run.json" in invocation.log) == (1, True)
    assert not Path("data/runs").exists()
