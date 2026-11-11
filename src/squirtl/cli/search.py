"""
Defines `search`, the command that searches for a path to the starter over
save states in a run of its own under `data/runs/`, or resumes a stopped
search in a new one.
"""

from cyclopts   import Parameter
from pathlib    import Path
from subprocess import CalledProcessError
from typing     import Annotated

from squirtl.cli.logs      import following, listen, refusing
from squirtl.runs.schemas  import Run, RunSettings
from squirtl.runs.searcher import Searcher


def search(
    *,
    resume   : Annotated[
        Path | None,
        Parameter(
            help = (
                "The directory of a stopped search to continue from its last "
                "checkpoint, under the settings that search recorded."
            )
        )
    ] = None,
    settings : Annotated[RunSettings | None, Parameter(name="*")] = None,
    verbose  : Annotated[
        bool, Parameter(help="Log each step beside the line each iteration logs.")
    ] = False
) -> str:
    """
    Searches for a path from Blue's bedroom to the starter over saved
    states, across `--search.workers` processes, ending once a particle sets
    `EVENT_GOT_STARTER` or the presses reach the run's `--steps`, logging a
    line per iteration above a progress bar.

    The run writes its record, a line per iteration, the path it finds so
    far, and a checkpoint into a directory of its own under `data/runs/`,
    which the command prints once the search ends, and `squirtl watch`
    plays that path. An interrupt, a termination signal, or `squirtl stop`
    ends the search at the end of its iteration with a checkpoint and exits
    0, and a second interrupt ends it at once on the last checkpoint and
    exits 130.

    Each of these exits 1 before any directory is made:

    - A `--resume` directory holding no search or no checkpoint
    - A checkpoint damaged, already holding the starter or the run's steps, or
      differing from the search the run's settings build
    - An iteration log ending short of that checkpoint
    - A cartridge the emulator refuses
    - A working directory no git clone holds
    """
    console = listen(verbose)

    with refusing(CalledProcessError, OSError, ValueError):
        searcher = Searcher.launch(resume and Run.read(resume), settings)

    with searcher:
        return following(console, searcher)
