"""
Defines the worker each rollout of a search runs in, `boot` making the
environment of its process and `roll` pressing through a `SearchRollout`
on it, which imports nothing beyond what that worker needs, since a spawned
process imports the module its worker sits in.
"""

from atexit import register
from gymnasium.envs.registration import EnvSpec
from os import setpgrp

from squirtl.environment.schemas import Entry
from squirtl.search.schemas      import Ending, SearchRollout


def boot(specification: EnvSpec):
    """
    Moves the process into a process group of its own, so the interrupt a
    terminal sends its foreground group and the termination signal `timeout`
    sends its own group reach only the main process, whose handler ends
    the search at its iteration's end, while the pool's `terminate` still
    reaches the worker. It then makes the environment `specification`
    describes, which every rollout the process runs restores, and closes
    it as the process exits, while the interpreter is still whole. A PyBoy
    left open until the interpreter's final collection raises there after
    `sys.excepthook` is gone, printing an empty report for each error.
    """
    global environment

    setpgrp()

    environment = specification.make()

    register(environment.close)


def roll(rollout: SearchRollout) -> Ending:
    """
    Restores the snapshot `rollout` starts from and presses each of its
    actions, stopping where `rollout` halts and a press has earned reward,
    since Mhammedi and Cohan's Algorithm 1 secures a reward as soon as
    a rollout finds it, and where Blue blacks out. The result depends on
    `rollout` alone, whichever process runs it.
    """
    observation, _ = environment.reset(options={"snapshot": rollout.snapshot})

    overworld = environment.unwrapped
    game_boy  = overworld.game_boy
    progress  = overworld.progress
    reward    = overworld.reward.total(progress.earned)
    tiles     = game_boy.tiles  # prose: ignore[inlinable-bindings]
    frames    = [observation[Entry.FRAMES][-1]]
    pressed   = bytearray()
    blackout  = False

    for action in rollout.presses:
        observation, *_ = environment.step(action)
        frames.append(observation[Entry.FRAMES][-1])
        pressed.append(action)

        if blackout := game_boy.blacked_out:
            break

        if rollout.halting and overworld.reward.total(progress.earned) > reward:
            break

    return Ending(
        dead = blackout or (
            progress.events       == rollout.snapshot.tally.events
            and progress.position == rollout.snapshot.tally.position
            and game_boy.tiles    == tiles
        ),
        frames   = b"".join(frames[1:]),
        presses  = bytes(pressed),
        reward   = overworld.reward.total(progress.earned),
        snapshot = environment.get_wrapper_attr("capture")()
    )
