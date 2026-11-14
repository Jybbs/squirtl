"""
Defines the worker each rollout of a search runs in, `boot` making the
environment of its process and `roll` pressing through a `SearchRollout`
on it, which imports nothing beyond what that worker needs, since a spawned
process imports the module its worker sits in.
"""

from atexit import register
from gymnasium.envs.registration import EnvSpec
from multiprocessing             import parent_process
from os        import _exit, setpgrp
from threading import Thread

from squirtl.environment.schemas import Entry
from squirtl.search.schemas      import Ending, SearchRollout


def boot(specification: EnvSpec):
    """
    Moves the process into a process group of its own, so the interrupt a
    terminal sends its foreground group and the termination signal `timeout`
    sends its own group reach only the main process, whose handler ends
    the search at its iteration's end, while the pool's `terminate` still
    reaches the worker. Since no signal to that group reaches the worker
    either, a thread of its own ends the worker once the main process has
    ended. It then makes the environment `specification` describes, which
    every rollout the process runs restores, and closes it as the process
    exits, while the interpreter is still whole. A PyBoy left open until the
    interpreter's final collection raises there after `sys.excepthook` is
    gone, printing an empty report for each error.
    """
    global environment

    setpgrp()

    Thread(daemon=True, target=exit_with_parent).start()

    environment = specification.make()

    register(environment.close)


def exit_with_parent():
    """
    Waits until the process that started the worker has ended, then ends the
    worker at once, since a worker the pool no longer reaches waits on its
    queue for good, holding its emulator.
    """
    parent_process().join()
    _exit(1)


def roll(rollout: SearchRollout) -> Ending:
    """
    Restores the snapshot `rollout` starts from and presses each of its
    actions, stopping where Blue blacks out, which reads at the faint of his
    last Pokémon, and where `rollout` halts and a press has set a flag the
    reward pays. A new square leaves the rollout playing, whereas line 8 of
    Mhammedi and Cohan's Algorithm 1 halts on any rise in reward. The ending
    holds the total `Progress` pays every term, and depends on `rollout`
    alone, whichever process runs it.
    """
    observation, _ = environment.reset(options={"snapshot": rollout.snapshot})

    overworld   = environment.unwrapped
    game_boy    = overworld.game_boy
    progress    = overworld.progress
    flag_reward = overworld.reward.total(progress.earned)
    start       = progress.total, game_boy.tiles  # prose: ignore[inlinable-bindings]
    frames      = [observation[Entry.FRAMES][-1]]
    pressed     = bytearray()
    blackout    = False

    for action in rollout.presses:
        observation, *_ = environment.step(action)
        frames.append(observation[Entry.FRAMES][-1])
        pressed.append(action)

        if blackout := progress.blacked_out:
            break

        if rollout.halting and overworld.reward.total(progress.earned) > flag_reward:
            break

    return Ending(
        dead = blackout or (
            progress.events       == rollout.snapshot.tally.events
            and progress.position == rollout.snapshot.tally.position
            and (progress.total, game_boy.tiles) == start
        ),
        frames   = b"".join(frames[1:]),
        presses  = bytes(pressed),
        reward   = progress.total,
        snapshot = environment.get_wrapper_attr("capture")()
    )
