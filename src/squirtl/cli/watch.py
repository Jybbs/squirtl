"""
Defines `watch`, the command that plays an episode a run recorded back
through the emulator's window.
"""

from cyclopts       import Parameter
from cyclopts.types import PositiveInt
from loguru         import logger
from pathlib        import Path
from typing         import Annotated

from squirtl.cli.logs              import listen, refusing
from squirtl.emulator.schemas      import Cartridge
from squirtl.environment.overworld import Overworld
from squirtl.runs.schemas          import Run


def watch(
    directory : Annotated[Path, Parameter(
        help = "The run's directory under `data/runs/`."
    )],
    *,
    episode   : Annotated[
        PositiveInt | None,
        Parameter(help="The episode to play, counting from 1, or none for the last.")
    ] = None
) -> int | None:
    """
    Opens the emulator's window and plays back one episode the run recorded,
    from the reset at the `timer_div` the run recorded for it to the return
    the run recorded, at the sixty steps a second the window paces.

    A directory holding no run, an episode the run never recorded, or a
    cartridge the emulator refuses exits 1 before the window opens, and
    a console whose intro leaves a state of another digest than the run's
    exits 1 before playing anything. A playback reaching a return other than
    the one recorded exits 1 once it ends.
    """
    listen()

    with refusing(IndexError, OSError, ValueError):
        run       = Run.read(directory)
        recorded  = run.episode(episode)
        cartridge = Cartridge.read(run.settings.emulator.cartridge)

    with Overworld(
        cartridge,
        run.settings.emulator.model_copy(update={"open_window": True}),
        run.settings.environment,
        run.settings.reward
    ) as overworld:
        if overworld.digest != run.digest:
            logger.error(
                "The intro left the console in a state of digest {}, where the run "
                "recorded {}",
                overworld.digest,
                run.digest
            )

            return 1

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
