"""
Defines `search`, the command that searches for a path to the run's goal
over save states in a run of its own under `data/runs/`, or resumes a
stopped search in a new one.
"""

from cyclopts   import Parameter
from datetime   import UTC, datetime
from subprocess import CalledProcessError
from typing     import Annotated

from squirtl.cli.logs         import drive, listen, refusing
from squirtl.cli.runs         import RunDirectory
from squirtl.emulator.schemas import Cartridge
from squirtl.runs.schemas     import Run, SearchRunSettings
from squirtl.runs.searcher    import SearchHandover, Searcher


def search(
    *,
    resume   : Annotated[
        RunDirectory | None,
        Parameter(
            help = (
                "The directory of a stopped search to continue from its last "
                "checkpoint, under the settings that search recorded."
            )
        )
    ] = None,
    settings : Annotated[SearchRunSettings | None, Parameter(name="*")] = None
) -> str:
    """
    Searches for a path from Blue's bedroom to `--environment.goal` over
    saved states, across `--search.workers` processes, ending once a
    particle sets the goal or the presses reach the run's `--steps`, logging
    a line per iteration above a progress bar.

    The run writes its record, a line per iteration, and a checkpoint
    into a directory of its own under `data/runs/`, which the command
    prints once the search ends, and the path to the goal, once it finds
    one, as an episode reaching it, which `squirtl watch` plays and
    `--curriculum.demonstration` reads. An interrupt, a termination signal,
    or `squirtl stop` ends the search at the end of its iteration with a
    checkpoint and exits 0, and a second interrupt ends it at once on the
    last checkpoint and exits 130.

    Each of these exits 1 before any directory is made:

    - A `--resume` directory holding no search or no checkpoint
    - A `--resume` directory holding a training run
    - A checkpoint damaged, already holding the goal or the run's steps, or
      differing from the search the run's settings build
    - An iteration log ending short of that checkpoint
    - A cartridge the emulator refuses
    - A working directory no git clone holds
    """
    console = listen()

    with refusing(CalledProcessError, OSError, ValueError):
        previous  = resume and Run.read(resume)
        handover  = previous and SearchHandover.from_run(previous)
        settings  = previous.settings if previous else settings or SearchRunSettings()
        cartridge = Cartridge.read(settings.emulator.cartridge)
        searcher  = Searcher(cartridge, settings, datetime.now(UTC), handover)

    with searcher:
        return drive(console, searcher)
