"""
Defines the records one run reads and writes:

- `RunSettings`, every setting the run reads
- `Revision`, the code the run ran on
- `Run`, the directory under `data/runs/` recording both
- `Stream`, the streams of random draws the run makes
"""

from dataclasses import asdict, dataclass
from datetime    import UTC, datetime
from enum        import StrEnum, auto
from hashlib     import blake2b, sha256
from json        import dumps
from pathlib     import Path
from subprocess  import check_output
from typing      import Self


class Stream(StrEnum):
    """
    The streams of random draws a run makes, each starting from a seed of
    its own, so no stream repeats the draws of another.
    """

    AGENT       = auto()
    ENVIRONMENT = auto()
    EVALUATION  = auto()


@dataclass(frozen=True, kw_only=True)
class Revision:
    """
    The code a run ran on, read from the clone in the working directory.
    """

    commit: str
    """
    The commit checked out, as `git rev-parse HEAD` prints it.
    """

    dirty: bool
    """
    Whether the working tree differs from the commit, which
    `git status --porcelain` reports for a changed tracked file and for an
    untracked one outside the paths `.gitignore` covers.
    """

    lockfile: str
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
            CalledProcessError: Where the working directory holds no git
                                clone.
        """
        return cls(
            commit   = check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            dirty    = bool(check_output(["git", "status", "--porcelain"])),
            lockfile = sha256(Path("uv.lock").read_bytes()).hexdigest()
        )


@dataclass(frozen=True, kw_only=True)
class RunSettings:
    """
    The settings one run reads, where each field is a flag on any command
    taking the record through `Parameter(name="*")` and a key under
    `[tool.squirtl]` in `pyproject.toml`.
    """

    seed: int = 1
    """
    The seed every random draw in the run derives from, 1 by default as in
    CleanRL's `dqn_atari.py`.
    """

    @property
    def seeds(self) -> dict[Stream, int]:
        """
        Derives the seed each stream starts from by hashing `seed` through
        BLAKE2b with the stream's name as the personalization string, so
        each stream takes a seed of its own that the same run seed always
        reproduces.

        Returns:
            Each stream's seed, a 64-bit unsigned integer.
        """
        return {
            stream: int.from_bytes(
                blake2b(str(self.seed).encode(), digest_size=8, person=stream.encode())
                .digest()
            )
            for stream in Stream
        }


@dataclass(frozen=True, kw_only=True)
class Run:
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

    started: datetime
    """
    The instant the run started.
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
        """
        run = cls(
            resumes  = resumes,
            revision = Revision.checked_out(),
            settings = settings,
            started  = started
        )
        run.directory.mkdir(parents=True)
        run.record.write_text(
            dumps(asdict(run), default=datetime.isoformat, indent=2),
            encoding = "utf-8"
        )

        return run
