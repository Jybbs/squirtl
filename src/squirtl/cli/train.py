"""
Defines `train`, the command that trains the agent in a run of its own under
`data/runs/`, or resumes a stopped run in a new one.
"""

from cyclopts      import Parameter
from datetime      import UTC, datetime
from pathlib       import Path
from rich.progress import Progress
from subprocess    import CalledProcessError
from typing        import Annotated

from squirtl.agent.schemas    import Checkpoint
from squirtl.cli.logs         import listen, refusing
from squirtl.emulator.schemas import Cartridge
from squirtl.runs.schemas     import Run, RunSettings
from squirtl.runs.trainer     import Trainer


def train(
    *,
    resume   : Annotated[
        Path | None,
        Parameter(
            help = (
                "The directory of a stopped run to continue from its last checkpoint, "
                "under the settings that run recorded."
            )
        )
    ] = None,
    settings : Annotated[RunSettings | None, Parameter(name="*")] = None,
    verbose  : Annotated[
        bool, Parameter(help="Log each step beside the line each episode logs.")
    ] = False
) -> str:
    """
    Trains the agent for the run's `--steps` environment steps, headless
    unless `--emulator.open-window` is set, logging a line per episode above
    a progress bar.

    The run writes its record, a line per episode, and a checkpoint into a
    directory of its own under `data/runs/`, which the command prints once
    the run ends. An interrupt, a termination signal, or `squirtl stop` ends
    the run at the end of its episode with a checkpoint and exits 0, and a
    second interrupt ends it at once on the last checkpoint and exits
    130.

    A `--resume` directory holding no run or no checkpoint, a cartridge
    the emulator refuses, or a working directory no git clone holds exits 1
    before any directory is made.
    """
    console = listen(verbose)

    with refusing(CalledProcessError, OSError, ValueError):
        previous   = resume and Run.read(resume)
        checkpoint = previous and Checkpoint.from_path(previous.checkpoint)
        settings   = previous.settings if previous else settings or RunSettings()
        cartridge  = Cartridge.read(settings.emulator.cartridge)
        run        = Run.start(settings, datetime.now(UTC), previous and previous.name)

    with Trainer(cartridge, run) as trainer:
        if previous:
            with refusing(ValueError):
                trainer.resume(checkpoint, previous)

        with Progress(console=console) as progress:
            task = progress.add_task(
                run.name,
                completed = trainer.agent.step,
                total     = settings.steps
            )

            # `Progress.track` drops the `completed` a task began at once it ends.
            for step in trainer:
                progress.update(task, completed=step)

    return str(run.directory)
