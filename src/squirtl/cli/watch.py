"""
Defines `watch`, the command that plays an episode a run recorded back
through the emulator's window.
"""

from cyclopts       import Parameter
from cyclopts.types import PositiveInt
from loguru         import logger
from typing         import Annotated

from squirtl.cli.logs              import listen, refusing
from squirtl.cli.runs              import ReleaseTag, RunDirectory, Selection
from squirtl.emulator.schemas      import Cartridge
from squirtl.environment.overworld import Overworld
from squirtl.releases.schemas      import RunSelection


def watch(
    directory : RunDirectory | None = None,
    *,
    episode   : Annotated[
        PositiveInt | None,
        Parameter(help="The episode to play, counting from 1, or none for the last.")
    ] = None,
    release   : ReleaseTag = None,
    selector  : Selection  = None
) -> int | None:
    """
    Opens the emulator's window and plays back one episode the run recorded,
    from the reset at the `timer_div` the run recorded for it to the return
    the run recorded, at the sixty steps a second the window paces.

    The run is the one a directory holds, or one of the runs `--release`
    attaches, fetched into `data/runs/` where it is missing there.
    `--agent`, `--start`, and `--seed` select it among the release's runs,
    and without them the release's recommended run plays.

    An episode that started along a demonstration plays the demonstration's
    presses up to its start first, and its return counts its own steps
    alone.

    Each of these exits 1 before the window opens:

    - Both a directory and `--release`, or neither
    - A directory holding no run, a release GitHub does not publish, or one
      attaching no manifest
    - A download whose digest differs or whose tar does not unpack
    - A selection matching no run of the release, or more than one, each
      of which it names
    - An episode the run never recorded, or a cartridge the emulator refuses

    A console whose intro leaves a state of another digest than the run's
    exits 1 before playing anything, and a playback reaching a return other
    than the one recorded exits 1 once it ends.
    """
    listen()

    with refusing(IndexError, OSError, ValueError):
        run = RunSelection(
            directories = (directory,) if directory else (),
            release     = release,
            selector    = selector
        ).one()
        recorded  = run.episode(episode)
        cartridge = Cartridge.read(run.settings.emulator.cartridge)

    with Overworld(
        cartridge,
        run.settings.emulator.model_copy(update={"open_window": True}),
        run.settings.environment,
        run.settings.reward
    ) as overworld:
        with refusing(ValueError):
            run.check(overworld.digest)

        reward = overworld.play(recorded.recording)

    if reward != recorded.reward:
        logger.error(
            "The playback reached a return of {} where the run recorded {}",
            reward,
            recorded.reward
        )

        return 1

    logger.info("The playback reached the return of {:.4f} the run recorded", reward)

    return None
