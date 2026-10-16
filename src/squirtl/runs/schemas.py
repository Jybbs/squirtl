"""
Defines the records one run reads and writes:

- `RunSettings`, every setting the run reads
- `Revision`, the code the run ran on
- `Run`, the directory under `data/runs/` recording both
- `Episode`, one episode as a line of the run's `episodes`
- `Stream`, the streams of random draws the run makes
"""

from collections     import deque
from collections.abc import Iterator
from datetime        import UTC, datetime
from enum            import StrEnum, auto
from hashlib         import sha256
from itertools       import islice
from numpy           import uint64
from numpy.random    import SeedSequence
from pathlib         import Path
from pydantic        import AwareDatetime, Field, NonNegativeInt, PositiveInt, StringConstraints
from subprocess      import check_output
from typing          import Annotated, Self

from squirtl.agent.schemas       import AgentSettings
from squirtl.emulator.schemas    import EmulatorSettings, Record
from squirtl.environment.schemas import EnvironmentSettings, Recording
from squirtl.reward.schemas      import RewardSettings, Term

type Hexadecimal = Annotated[
    str, StringConstraints(pattern=r"^[0-9a-f]+$", strip_whitespace=True)
]


class Revision(Record):
    """
    The code a run ran on, read from the clone in the working directory.
    """

    commit: Hexadecimal
    """
    The commit checked out, as `git rev-parse HEAD` prints it.
    """

    dirty: bool
    """
    Whether the working tree differs from the commit, which
    `git status --porcelain --untracked-files=normal` reports for a changed
    tracked file and for an untracked one outside the paths git ignores.
    """

    lockfile: Hexadecimal
    """
    The SHA-256 digest of `uv.lock`, which pins every library the run
    imports.
    """

    @classmethod
    def checked_out(cls) -> Self:
        """
        Reads the commit the working directory's clone has checked out,
        whether its working tree differs from it, and the digest of its
        `uv.lock`.

        Raises:
            CalledProcessError : Where the working directory holds no git
                                 clone.
            FileNotFoundError  : Where the working directory holds no
                                 `uv.lock` or no `git` is on the search
                                 path.
        """
        return cls(
            commit = check_output(["git", "rev-parse", "HEAD"], text=True),
            dirty  = bool(
                check_output(
                    ["git", "status", "--porcelain", "--untracked-files=normal"]
                )
            ),
            lockfile = sha256(Path("uv.lock").read_bytes()).hexdigest()
        )


class Stream(StrEnum):
    """
    The streams of random draws a run makes, each starting from a seed of
    its own, so no stream repeats the draws of another.
    """

    AGENT       = auto()
    ENVIRONMENT = auto()
    EVALUATION  = auto()


class RunSettings(Record):
    """
    The settings one run reads, where each field is a flag on any
    command that flattens the record through `Parameter(name="*")` and
    a key under `[tool.squirtl]` in `pyproject.toml`. A field holding
    a subject's record takes that record's fields as flags under its
    name (`--emulator.cartridge`) and as keys of a table of its own
    (`[tool.squirtl.emulator]`). A bare `*` before the record in the
    command's signature keeps every field keyword-only, so no bare token
    fills one.
    """

    agent: AgentSettings = Field(default_factory=AgentSettings)
    """
    The settings the agent reads.
    """

    checkpoint_steps: PositiveInt = 250_000
    """
    The environment steps past which the next episode's end writes a
    checkpoint, whose default is the 250,000 steps of each iteration
    Dopamine's DQN checkpoints after.
    """

    emulator: EmulatorSettings = Field(default_factory=EmulatorSettings)
    """
    The settings the emulator reads.
    """

    environment: EnvironmentSettings = Field(default_factory=EnvironmentSettings)
    """
    The settings the environment reads.
    """

    reward: RewardSettings = Field(default_factory=RewardSettings)
    """
    The settings the reward reads.
    """

    seed: NonNegativeInt = 1
    """
    The seed every random draw in the run derives from, whose default
    follows CleanRL's `dqn_atari.py`.
    """

    steps: PositiveInt = 10_000_000
    """
    The environment steps the run takes, whose default follows CleanRL's
    `dqn_atari.py`.
    """

    @property
    def seeds(self) -> dict[Stream, int]:
        """
        Spawns one child of a `SeedSequence` over `seed` for each stream,
        in the order `Stream` declares its members, and draws each child's
        seed.

        Returns:
            Each stream's seed, a 64-bit unsigned integer, which
            `torch.manual_seed` and Gymnasium's `reset` both take.
        """
        return {
            stream: child.generate_state(1, uint64).item()
            for stream, child in zip(Stream, SeedSequence(self.seed).spawn(len(Stream)))
        }


class Run(Record):
    """
    One run, recorded in a directory of its own under `data/runs/` named for
    the instant it started.
    """

    revision: Revision
    """
    The code the run ran on.
    """

    settings: RunSettings
    """
    The settings the run read.
    """

    started: AwareDatetime
    """
    The instant the run started, carrying the UTC offset `name` reads to
    spell it in UTC.
    """

    resumes: str | None = None
    """
    The name of the run this one continues, or `None` for a run starting
    afresh.
    """

    @property
    def checkpoint(self) -> Path:
        """
        Locates the checkpoint a run writes at each interval and at its end,
        which a resumed run continues training from.
        """
        return self.directory / "checkpoint.npz"

    @property
    def directory(self) -> Path:
        """
        Locates the directory under `data/runs/` holding everything the
        run writes.
        """
        return Path("data/runs", self.name)

    @property
    def episodes(self) -> Path:
        """
        Locates the JSON Lines file holding one `Episode` per line, in the
        order the run played them.
        """
        return self.directory / "episodes.jsonl"

    @property
    def name(self) -> str:
        """
        Spells `started` in UTC in the basic format of ISO 8601 to the
        microsecond, which `datetime.fromisoformat` reads back.
        """
        return f"{self.started.astimezone(UTC):%Y%m%dT%H%M%S.%fZ}"

    @property
    def record(self) -> Path:
        """
        Locates the JSON file holding the run's settings, its revision, the
        instant it started, and the run it resumes.
        """
        return self.directory / "run.json"

    @property
    def recorded(self) -> Iterator[Episode]:
        """
        Reads each episode `episodes` holds, in the order the run played
        them, reading each line only once a caller draws its episode.
        """
        with self.episodes.open(encoding="utf-8") as lines:
            yield from map(Episode.model_validate_json, lines)

    @property
    def stop(self) -> Path:
        """
        Locates the file whose presence stops the run at the end of the
        episode it is playing, which `squirtl stop` writes.
        """
        return self.directory / "stop"

    def ended_by(self, step: int) -> Iterator[Episode]:
        """
        Reads each episode `episodes` holds that ended by `step` of the run,
        meaning each whose steps and the steps before it total no more. It
        reads no line past the episode ending on or after `step`, so a line
        the run left half written past its checkpoint stays unread.
        """
        taken = 0

        for episode in self.recorded:
            taken += episode.length

            if taken > step:
                return

            yield episode

            if taken == step:
                return

    def episode(self, number: int | None = None) -> Episode:
        """
        Reads episode `number` of `episodes`, counting from 1, or the last
        where `number` is `None`, holding no other episode in memory.

        Raises:
            IndexError: Where `episodes` holds no such episode.
        """
        if found := deque(
            islice(self.recorded, number and number - 1, number),
            maxlen = 1
        ):
            return found[0]

        raise IndexError(f"{self.episodes} holds no episode {number or 'at all'}")

    @classmethod
    def read(cls, directory: Path) -> Self:
        """
        Reads the run whose record `directory` holds.

        Raises:
            FileNotFoundError : Where `directory` holds no record.
            ValidationError   : Where the record holds no run.
            ValueError        : Where `directory` is not the directory under
                                `data/runs/` the run's name gives, the place
                                every path of the run is read from.
        """
        run = cls.model_validate_json(
            (directory / "run.json").read_text(encoding="utf-8")
        )

        if directory.resolve() != run.directory.resolve():
            raise ValueError(
                f"{directory} holds the run {run.name}, which a command reads "
                f"from {run.directory} under the working directory"
            )

        return run

    @classmethod
    def start(
        cls,
        settings : RunSettings,
        started  : datetime,
        resumes  : str | None = None
    ) -> Self:
        """
        Creates the directory of a run reading `settings` from `started` on
        and writes its record there, holding those settings, that instant,
        and the revision of the clone in the working directory.

        Args:
            resumes: The name of the run this one continues, or `None` for a
                     run starting afresh.

        Raises:
            CalledProcessError : Where the working directory holds no git
                                 clone.
            FileExistsError    : Where a run started at the same instant
                                 already holds the directory, which is left
                                 as it was.
            FileNotFoundError  : Where the working directory holds no
                                 `uv.lock` or no `git` is on the search
                                 path, before any directory is created.
            ValidationError    : Where `started` carries no UTC offset,
                                 before any directory is created.
        """
        run = cls(
            resumes  = resumes,
            revision = Revision.checked_out(),
            settings = settings,
            started  = started
        )
        run.directory.mkdir(parents=True)
        run.record.write_text(run.model_dump_json(indent=2), encoding="utf-8")

        return run


class Episode(Record):
    """
    One episode as a run records it on a line of its `episodes`, from what
    the episode earned to the `Recording` that `squirtl watch` plays back.
    """

    epsilon: float
    """
    The chance of a random action at the episode's last step.
    """

    length: int
    """
    The steps the episode took.
    """

    loss: float | None
    """
    The mean Huber loss over the updates the episode's steps took, or `None`
    where replay memory held too few transitions for any.
    """

    positions: int
    """
    The positions the episode reached, the one it started on included.
    """

    recording: Recording
    """
    The start, the `timer_div`, and the presses the emulator plays the
    episode back from.
    """

    reward: float
    """
    The reward the episode's steps total, its return.
    """

    seconds: float
    """
    The wall time from the episode's reset to its last step, in seconds.
    """

    shares: dict[Term, float]
    """
    Each term's part of `reward`.
    """

    terminated: bool
    """
    Whether the episode ended at the starter, where otherwise `TimeLimit`
    truncated it.
    """

    value: float | None
    """
    The mean value the online network gave the actions of each update's
    batch, or `None` where no update ran.
    """
