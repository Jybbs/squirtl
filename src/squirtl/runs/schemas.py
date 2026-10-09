"""
Defines the records one run reads and writes:

- `RunSettings`, every setting the run reads
- `Revision`, the code the run ran on
- `Run`, the directory under `data/runs/` recording both
- `Stream`, the streams of random draws the run makes
"""

from datetime     import UTC, datetime
from enum         import StrEnum, auto
from hashlib      import sha256
from numpy        import uint64
from numpy.random import SeedSequence
from pathlib      import Path
from pydantic     import AwareDatetime, Field, NonNegativeInt, StringConstraints
from subprocess   import check_output
from typing       import Annotated, Self

from squirtl.agent.schemas    import AgentSettings
from squirtl.emulator.schemas import EmulatorSettings, Record

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

    emulator: EmulatorSettings = Field(default_factory=EmulatorSettings)
    """
    The settings the emulator reads.
    """

    seed: NonNegativeInt = 1
    """
    The seed every random draw in the run derives from, whose default
    follows CleanRL's `dqn_atari.py`.
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
            for stream, child in zip(
                Stream,
                SeedSequence(self.seed).spawn(len(Stream)),
                strict = True
            )
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
    def directory(self) -> Path:
        """
        Locates the directory under `data/runs/` holding everything the
        run writes.
        """
        return Path("data/runs", self.name)

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
