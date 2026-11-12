"""
Defines `train`, the command that trains the agent in a run of its own under
`data/runs/`, or resumes a stopped run in a new one.
"""

from cyclopts      import Parameter
from datetime      import UTC, datetime
from rich.progress import Progress
from subprocess    import CalledProcessError
from typing        import Annotated

from squirtl.cli.logs         import listen, refusing
from squirtl.cli.runs         import RunDirectory
from squirtl.emulator.schemas import Cartridge
from squirtl.runs.schemas     import Run, RunSettings
from squirtl.runs.trainer     import Handover, Trainer


def train(
    *,
    resume   : Annotated[
        RunDirectory | None,
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
    Trains the agent `--agent.algorithm` names for the run's `--steps`
    environment steps, headless unless `--emulator.open-window` is set,
    logging a line per episode above a progress bar.

    A setting on by default turns off as `--agent.double-q=false` does.

    The run writes its record, a line per episode, and a checkpoint into a
    directory of its own under `data/runs/`, which the command prints once
    the run ends. An interrupt, a termination signal, or `squirtl stop` ends
    the run with a checkpoint and exits 0, at the end of its episode for the
    deep Q-network and once a rollout's update ends for PQN and PPO, and a
    second interrupt ends it at once on the last checkpoint and exits 130.

    Each of these exits 1 before any directory is made:

    - A `--resume` directory holding no run or no checkpoint
    - A `--curriculum.demonstration` directory holding no run, a run whose
      episodes end at another `--environment.goal` than this run's, no
      episode reaching that goal from Blue's bedroom, or one whose presses
      no longer reach it on replay
    - A checkpoint damaged, already holding the run's steps, or differing
      from the agent the run's settings build
    - A checkpoint whose segments end at other steps than the segments of
      its demonstration now do
    - An episode log ending short of that checkpoint
    - A cartridge the emulator refuses
    - A working directory no git clone holds
    """
    console = listen(verbose)

    with refusing(CalledProcessError, OSError, ValueError):
        previous  = resume and Run.read(resume)
        handover  = previous and Handover.from_run(previous)
        settings  = previous.settings if previous else settings or RunSettings()
        cartridge = Cartridge.read(settings.emulator.cartridge)
        trainer   = Trainer.start(cartridge, settings, datetime.now(UTC), handover)

    with trainer:
        with Progress(console=console) as progress:
            task = progress.add_task(
                trainer.run.name,
                completed = trainer.agent.step,
                total     = settings.steps
            )

            # `Progress.track` drops the `completed` a task began at once it ends.
            for step in trainer:
                progress.update(task, completed=step)

    return str(trainer.run.directory)
