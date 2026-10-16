"""
Pins what `squirtl train` does, covering:

- The run it writes under `data/runs/` and the directory it prints
- The cartridge, the `--resume` directory, and the working directory outside
  a clone it refuses before making any directory, a run holding no checkpoint
  among them
- A resume into a new directory under the settings the stopped run recorded
- The line each episode logs and the line each step logs under `--verbose`
- The emulator's window `--emulator.open-window` opens
"""

from common.cli import Invoker
from pathlib    import Path
from pytest     import MonkeyPatch, mark, param

from squirtl.agent.schemas import Checkpoint
from squirtl.runs.schemas  import Run


def test_a_resume_continues_in_a_new_directory_under_the_recorded_settings(
    invoke  : Invoker,
    trained : Path
):
    """
    Asserts that resuming a run writes a new directory naming the run it
    continues, under the settings that run recorded whatever the flags set,
    holding that run's lines and a checkpoint of its own.
    """
    invocation = invoke(["train", "--resume", str(trained), "--steps", "99"])
    resumed    = Run.read(Path(invocation.output.strip()))

    assert (invocation.code, resumed.resumes, resumed.settings) == (
        0, trained.name,
        Run.read(trained).settings
    )
    assert (
        resumed.episodes.read_text(encoding="utf-8"),
        Checkpoint.from_path(resumed.checkpoint).step
    ) == (Run.read(trained).episodes.read_text(encoding="utf-8"), 10)


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
    `Edition` lists exits 1, logging the refusal, and makes no directory
    under `data/runs/`.
    """
    invocation = invoke(["train", *quick])

    assert (
        invocation.code,
        "is not the English Pokémon Blue ROM" in invocation.log
    ) == (
        1, True
    )
    assert not Path("data/runs").exists()


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


@mark.usefixtures("accepted", "rom")
def test_a_working_directory_no_clone_holds_exits_1_before_making_any_directory(
    invoke      : Invoker,
    monkeypatch : MonkeyPatch,
    quick       : list[str],
    tmp_path    : Path
):
    """
    Asserts that a run started where no git clone holds the working
    directory exits 1, logging the `git` command that failed in place of a
    traceback, and makes no directory there.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
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
    `--verbose` a line for each of its ten steps beside them.
    """
    log = invoke(["train", *quick, *flags]).log

    assert (log.count("Episode "), log.count("Step ")) == (2, logged)


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
        Checkpoint.from_path(run.checkpoint).step
    ) == (Path("data/runs"), 2, 10)


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
