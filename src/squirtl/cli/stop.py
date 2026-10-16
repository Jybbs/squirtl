"""
Defines `stop`, the command that writes the stop file ending a training run
at the end of the episode it is playing.
"""

from loguru  import logger
from pathlib import Path

from squirtl.cli.logs     import listen, refusing
from squirtl.runs.schemas import Run


def stop(directory: Path):
    """
    Writes the stop file that ends the run training in the directory given
    at the end of the episode it is playing, from any shell, where the run
    writes a checkpoint and exits 0 as it does on a first interrupt.

    A directory holding no run exits 1.

    Args:
        directory: The run's directory, under `data/runs/` in the clone it
                   trains in.
    """
    listen()

    with refusing(OSError, ValueError):
        run = Run.read(directory)

    run.stop.touch()
    logger.info(
        "Wrote the stop file ending the run in {} at its episode's end",
        run.directory
    )
