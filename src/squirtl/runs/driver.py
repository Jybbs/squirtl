"""
Defines `Driver`, what a training run and a search share as the loop of one
run, which takes over the signals that stop it and writes its checkpoint.
"""

from abc             import ABC, abstractmethod
from collections.abc import Iterator
from contextlib      import AbstractContextManager
from loguru          import logger
from pathlib         import Path
from signal          import SIGINT, SIGTERM, signal
from types           import FrameType
from typing          import ClassVar, Protocol, Self

from squirtl.runs.schemas import Run


class Saving(Protocol):
    """
    The checkpoint a driver writes, which `save` writes to a path.
    """

    def save(self, path: Path):
        """
        Writes the checkpoint to `path`.
        """


class Driver(AbstractContextManager, ABC):
    """
    The loop of one run, which stops where it next pauses on the first
    signal or on finding the run's `stop` file, and at once on the next
    signal, and writes its checkpoint at each interval and at its end.
    """

    pause: ClassVar[str]
    """
    Where a stopped run ends, naming the point at which its loop pauses.
    """

    def __enter__(self) -> Self:
        """
        Takes over the interrupt and termination signals for `interrupt`,
        keeping the handlers they had for `__exit__` to put back.
        """
        self.handlers = {
            number: signal(number, self.interrupt) for number in (SIGINT, SIGTERM)
        }

        return self

    def __exit__(self, *raised: object):
        """
        Puts back the handlers each signal had before `__enter__`, whether
        or not the `with` block raised.
        """
        for number, handler in self.handlers.items():
            signal(number, handler)

    def __init__(self, run: Run):
        """
        Drives `run`, no signal having arrived yet and nothing yet saved.
        """
        self.interrupted = False
        self.run         = run
        self.saved       = 0

    @abstractmethod
    def __iter__(self) -> Iterator[int]:
        """
        Runs the loop to its end, yielding `step` as it goes.
        """

    @property
    @abstractmethod
    def checkpointed(self) -> Saving:
        """
        Gathers everything a resumed run continues from.
        """

    @property
    @abstractmethod
    def logs(self) -> tuple[Path, ...]:
        """
        Lists the run's JSON Lines files a checkpoint follows.
        """

    @property
    @abstractmethod
    def step(self) -> int:
        """
        Reads the environment steps the run has taken.
        """

    @property
    def stopping(self) -> bool:
        """
        Reads whether the run stops where its loop next pauses, which a
        signal `interrupt` caught or the run's `stop` file sets.
        """
        return self.interrupted or self.run.stop.exists()

    def checkpoint(self):
        """
        Writes each of the run's `logs` through to disk, then the checkpoint
        to the run's `checkpoint`, and records the step it landed at, so no
        checkpoint runs ahead of the lines recorded before it.
        """
        for path in self.logs:
            self.run.sync(path)

        self.checkpointed.save(self.run.checkpoint)
        self.saved = self.step

        logger.info("Wrote the checkpoint at step {:,}", self.saved)

    def conclude(self, finished: str):
        """
        Ends the loop of a run that has `finished` its units of work,
        logging the `stop` file where it found one and writing a checkpoint,
        unless the run's own checkpoint already holds the last step.
        """
        if self.run.stop.exists():
            logger.warning(
                "Stopping at step {:,} after {} on finding {}",
                self.step,
                finished,
                self.run.stop
            )

        if self.saved < self.step or not self.run.checkpoint.exists():
            self.checkpoint()

    def due(self, interval: int, last: int) -> bool:
        """
        Reads whether the run's step has reached the first multiple of
        `interval` after `last`, the step a checkpoint or an evaluation
        last landed at, the one a resumed run continues from included, or 0
        before the first.
        """
        return self.step >= (last // interval + 1) * interval

    def interrupt(self, number: int, frame: FrameType | None):  # prose: ignore[unsorted-positionals]
        """
        Stops the run where its loop next pauses on the first interrupt
        or termination signal, and raises `KeyboardInterrupt` on the next,
        which ends the run at once on its last checkpoint.

        Raises:
            KeyboardInterrupt: On any signal after the first.
        """
        if self.interrupted:
            logger.warning("Ending at once on the last checkpoint")

            raise KeyboardInterrupt

        self.interrupted = True

        logger.warning(
            "Stopping at the end of the {}, where another interrupt ends the run at "
            "once on its last checkpoint",
            self.pause
        )
