"""
Pins what `squirtl watch` does, covering:

- An episode played back through the emulator's window to the return the
  run recorded, the last by default and any other the flag names
- The playback reaching another return, an episode the run never recorded,
  and a directory holding no run, each exiting 1
"""

from common.cli import Invoker
from json       import dumps, loads
from pathlib    import Path
from pytest     import mark, param

from squirtl.runs.schemas import Run


@mark.parametrize(
    "flags",
    [param([], id="the-last"), param(["--episode", "1"], id="the-first")]
)
def test_an_episode_plays_back_in_the_window_to_the_return_the_run_recorded(
    flags   : list[str],
    invoke  : Invoker,
    trained : Path,
    windows : list[str]
):
    """
    Asserts that playing back the run's last episode, or the one the flag
    names, boots the emulator in its SDL2 window and exits zero on reaching
    the return the run recorded, which it logs.
    """
    windows.clear()
    invocation = invoke(["watch", str(trained), *flags])

    assert (invocation.code, windows) == (0, ["SDL2"])
    assert "reached the return of 0.0 the run recorded" in invocation.log


def test_a_playback_reaching_another_return_exits_1(
    invoke  : Invoker,
    trained : Path,
    windows : list[str]
):
    """
    Asserts that a playback whose steps reach a return other than the one
    the line records exits 1, logging both returns.
    """
    run   = Run.read(trained)
    lines = [loads(line) for line in (
        run.episodes.read_text(encoding="utf-8")
           .splitlines()
    )]
    lines[-1]["reward"] = 0.5
    run.episodes.write_text(
        "".join(f"{dumps(line)}\n" for line in lines),
        encoding = "utf-8"
    )
    invocation = invoke(["watch", str(trained)])

    assert (
        invocation.code,
        "a return of 0.0 where the run recorded 0.5" in invocation.log
    ) == (
        1, True
    )


@mark.parametrize(
    "argv",
    [
        param(["--episode", "3"], id="an-episode-past-the-last"),
        param([],                 id="no-run")
    ]
)
def test_a_playback_with_nothing_to_play_exits_1_before_the_window_opens(
    argv    : list[str],
    invoke  : Invoker,
    trained : Path,
    windows : list[str]
):
    """
    Asserts that naming an episode past the two the run recorded, or a
    directory holding no run, exits 1 before any emulator boots.
    """
    windows.clear()
    invocation = invoke(["watch", str(trained if argv else trained.parent), *argv])

    assert (invocation.code, windows) == (1, [])
    assert ("holds no episode 3" in invocation.log) is bool(argv)
