"""
Defines `Curriculum`, which moves the window each segment of a demonstration
draws its starts from back toward Blue's bedroom as Mhammedi and Cohan's
Appendix B moves it, beside the records a checkpoint keeps of it, `Segment`
and `Syllabus`.
"""

from loguru       import logger
from numpy.random import default_rng
from statistics   import fmean

from squirtl.emulator.schemas    import Record
from squirtl.environment.schemas import Starts, Takeover, Window
from squirtl.runs.settings       import CurriculumSettings


class Segment(Record):
    """
    One segment of the demonstration, from its start up to the step whose
    press first sets one of the flags the reward pays, beside the window its
    episodes start from.
    """

    end: int
    """
    The step of the demonstration whose press first sets the segment's flag,
    the latest any start of the segment takes.
    """

    latest: int
    """
    The latest step the segment's window starts an episode at, from `end`
    back to 0.
    """

    moves: int = 0
    """
    The times the window has moved, which each start drawn from it carries,
    so an episode drawn before the last move stays out of `recent`.
    """

    recent: list[bool] = []
    """
    Whether each episode drawn from the window since its last move
    succeeded.
    """

    solved: bool = False
    """
    Whether the window has reached Blue's bedroom and the share of its
    episodes that succeed there has reached the completion share, after
    which no episode starts from it.
    """


class Syllabus(Record):
    """
    The curriculum as a checkpoint keeps it, so a resumed run moves each
    window as an unbroken one would.
    """

    average: float | None
    """
    The moving average of the lengths of the episodes from a start that
    succeeded, or `None` before the first.
    """

    generator: dict[str, object]
    """
    The state of the generator each move of a window draws its size from.
    """

    segments: list[Segment]
    """
    Each segment, in the order the demonstration reaches their ends.
    """


class Curriculum:
    """
    The windows of the segments of one demonstration, each moving back
    toward Blue's bedroom once enough of the recent episodes from it succeed
    and forward where too few do, beside the moving average of the lengths
    of the episodes that succeeded, which caps each episode's length.
    """

    def __init__(self, ends: list[int], seed: int, settings: CurriculumSettings):
        """
        Starts each segment's window at the step of the demonstration whose
        press sets its flag, which `ends` lists, with the generator moving
        each window seeded at `seed`.
        """
        self.average   = None
        self.generator = default_rng(seed)
        self.segments  = [Segment(end=end, latest=end) for end in ends]
        self.settings  = settings

    @property
    def limit(self) -> int:
        """
        Reads the steps after which an episode from a start truncates, the
        `multiplier` times the moving average of successful lengths plus the
        `buffer`, which before the first success is the buffer alone.
        """
        settings = self.settings

        return round(settings.multiplier * (self.average or 0) + settings.buffer)

    @property
    def starts(self) -> Starts | None:
        """
        Reads the window of each segment not yet solved, the `window` steps
        up to its latest start, none starting before Blue's bedroom.

        Returns:
            The windows beside `limit`, or `None` once every segment is
            solved, after which every episode starts in Blue's bedroom.
        """
        windows = [
            Window(
                earliest = max(0, segment.latest - self.settings.window),
                latest   = segment.latest,
                moves    = segment.moves,
                segment  = number
            )
            for number, segment in enumerate(self.segments) if not segment.solved
        ]

        return Starts(limit=self.limit, windows=windows) if windows else None

    @property
    def syllabus(self) -> Syllabus:
        """
        Gathers the moving average, the generator's state, and each segment
        for a checkpoint.
        """
        return Syllabus(
            average   = self.average,
            generator = self.generator.bit_generator.state,
            segments  = self.segments
        )

    def attempted(self, length: int, succeeded: bool, takeover: Takeover):
        """
        Takes in an episode of `length` steps started at `takeover`, adding
        its length to the moving average where it succeeded, and counting
        it toward its segment's share where its window has not moved since.
        Once `recent` episodes accumulate, it solves the segment, moves its
        window back, or moves it forward, then starts the count again.

        The average starts at the first successful length and gives each
        later one the weight `smoothing`, the rest staying on the average.
        """
        settings = self.settings

        if succeeded:
            last         = length if self.average is None else self.average
            self.average = settings.smoothing * length + (1 - settings.smoothing) * last

        number  = takeover.segment
        segment = self.segments[number]

        if segment.solved or takeover.moves != segment.moves:
            return

        recent = [*segment.recent, succeeded]

        if len(recent) < settings.recent:
            self.segments[number] = segment.model_copy(update={"recent": recent})

            return

        share = fmean(recent)

        if segment.latest == 0 and share >= settings.completion:
            latest, solved = 0, True
        elif share >= settings.required:
            move           = self.generator.uniform(*settings.back) * settings.window
            latest, solved = max(0, segment.latest - round(move)), False
        else:
            move           = self.generator.uniform(*settings.forward) * settings.window
            latest, solved = min(segment.end, segment.latest + round(move)), False

        self.segments[number] = Segment(
            end    = segment.end,
            latest = latest,
            moves  = segment.moves + 1,
            solved = solved
        )

        logger.info(
            "Segment {} {} after {:.0%} of its last {:,} episodes succeeded",
            number,
            "is solved" if solved else f"starts by step {latest:,}",
            share,
            settings.recent
        )

    def restore(self, syllabus: Syllabus):
        """
        Sets the moving average, the generator, and each segment to what
        `syllabus` holds.

        Raises:
            ValueError: Where the segments of `syllabus` end at other steps
                        than the demonstration's do now.
        """
        ends, taken = (
            [segment.end for segment in segments]
            for segments in (self.segments, syllabus.segments)
        )

        if taken != ends:
            raise ValueError(
                f"the checkpoint's segments end at steps {taken}, whereas the "
                f"demonstration's now end at steps {ends}"
            )

        self.average = syllabus.average
        self.generator.bit_generator.state = syllabus.generator
        self.segments = list(syllabus.segments)
