"""
Defines `stop`, the command that writes the stop file ending a training run
at the end of the episode it is playing or the rollout it is collecting, or
a search at the end of its iteration.
"""

from loguru  import logger

from squirtl.cli.logs     import listen, refusing
from squirtl.cli.runs     import RunDirectory
from squirtl.runs.schemas import Run


def stop(directory: RunDirectory):
    """
    Writes the stop file into a run's directory from any shell, ending the
    run with a checkpoint and exit status 0, as a first interrupt does, at
    the end of its episode for the deep Q-network, once a rollout's update
    ends for PQN and PPO, and at the end of its iteration for a search.

    A directory holding no run exits 1.
    """
    listen()

    with refusing(OSError, ValueError):
        run = Run.read(directory)

    run.stop.touch()
    logger.info(
        "Wrote the stop file ending the run in {}",
        run.directory
    )
