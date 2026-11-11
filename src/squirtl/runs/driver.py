"""
Defines `Driver`, what a training run and a search share as the loop of one
run, which takes over the signals that stop it.
"""

from abc        import abstractmethod
from contextlib import AbstractContextManager
from datetime   import UTC, datetime
from loguru     import logger
from signal     import SIGINT, SIGTERM, signal
from types      import FrameType
from typing     import ClassVar, Self

from squirtl.agent.schemas     import Checkpoint
from squirtl.emulator.schemas  import Cartridge
from squirtl.runs.schemas      import Handover, Run, RunSettings, SearchHandover
from squirtl.search.checkpoint import SearchCheckpoint


class Driver(AbstractContextManager):
    """
    The loop of one run, which stops at the end of its current unit of work
    on the first signal or on finding the run's `stop` file, and at once on
    the next signal.
    """

    handover: ClassVar[type[Handover | SearchHandover]]
    """
    The record a resumed run reads from the stopped run it continues.
    """

    unit: ClassVar[str]
    """
    The unit of work the run stops at the end of.
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

    @property
    @abstractmethod
    def state(self) -> Checkpoint | SearchCheckpoint:
        """
        Gathers what a resumed run continues from.
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
        Reads whether the run stops at the end of its current unit of work,
        which a signal `interrupt` caught or the run's `stop` file sets.
        """
        return self.interrupted or self.run.stop.exists()

    def checkpoint(self):
        """
        Writes the run's `log` through to disk, then `state` to the run's
        `checkpoint`, and records the step it landed at in `saved`, so no
        checkpoint runs ahead of the lines recorded before it.
        """
        self.run.sync(self.run.log)
        self.state.save(self.run.checkpoint)
        self.saved = self.step

        logger.info("Wrote the checkpoint at step {:,}", self.saved)

    def conclude(self, units: int):
        """
        Ends the loop of a run that finished `units` units of work, logging
        the `stop` file where it found one and writing a checkpoint, unless
        the run's own checkpoint already holds the last step.
        """
        if self.run.stop.exists():
            logger.warning(
                "Stopping at the end of {} {:,} on finding {}",
                self.unit,
                units,
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
        Stops the run at the end of its current unit of work on the first
        interrupt or termination signal, and raises `KeyboardInterrupt` on
        the next, which ends the run at once on its last checkpoint.

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
            self.unit
        )

    @classmethod
    def launch(cls, previous: Run | None, settings: RunSettings | None) -> Self:
        """
        Builds the driver of a run starting now on the cartridge its
        settings name, continuing `previous` under the settings it recorded
        where there is one, and otherwise under `settings` or the defaults.

        Raises:
            FileNotFoundError : Where `previous` holds no checkpoint, as
                                `handover.from_run` raises.
            ValueError        : Where what `previous` holds cannot be
                                continued, as `handover.from_run` raises,
                                beside each error `Cartridge.read` and the
                                driver raise.
        """
        handover = previous and cls.handover.from_run(previous)
        settings = previous.settings if previous else settings or RunSettings()

        return cls(
            Cartridge.read(settings.emulator.cartridge),
            settings,
            datetime.now(UTC),
            handover
        )
