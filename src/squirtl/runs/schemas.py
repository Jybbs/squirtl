"""
Defines the records one run writes:

- `Revision`, the code the run ran on
- `Run`, the directory under `data/runs/` recording the run's settings and
  its revision, each episode, each evaluation, and the checkpoint, or each
  iteration of a search
- `RunListing`, the settings naming a run among others, and `Start`, where
  its training episodes start
- `Episode`, one episode as a line of the run's `episodes`
"""

from collections     import deque
from collections.abc import Iterable, Iterator
from datetime        import UTC, datetime
from enum            import StrEnum, auto
from hashlib         import sha256
from itertools       import islice, takewhile
from json            import loads
from loguru          import logger
from operator        import attrgetter
from os              import SEEK_END, pread
from pathlib         import Path
from pydantic        import AwareDatetime, PrivateAttr, StringConstraints, ValidationError
from subprocess      import check_output
from typing          import Annotated, ClassVar, Self

from squirtl.agent.schemas       import Algorithm, PolicyUpdate, Update, flush
from squirtl.emulator.schemas    import Record, failures
from squirtl.environment.schemas import Outcome, Recording
from squirtl.evaluation.schemas  import Evaluation
from squirtl.runs.settings       import RunSettings

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


class Start(StrEnum):
    """
    Where a run's training episodes start, in Blue's bedroom or along the
    demonstration its curriculum names.
    """

    BEDROOM    = auto()
    CURRICULUM = auto()


class Run(Record):
    """
    One run, recorded in a directory of its own under `data/runs/` named for
    the instant it started.
    """

    file   : ClassVar[str]  = "run.json"
    folder : ClassVar[Path] = Path("data/runs")

    digest: Hexadecimal
    """
    The SHA-256 digest of the state `GameBoy.start` leaves the console in,
    the one a reset at a `timer_div` of 0 also leaves, which `squirtl watch`
    checks before playing an episode back.
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

    _read_from: Path | None = PrivateAttr(None)
    """
    The directory `read` read the run from, or `None` for a run built in
    the working directory.
    """

    resumes: str | None = None
    """
    The name of the run this one continues, or `None` for a run starting
    afresh.
    """

    searches: bool = False
    """
    Whether the run is a search over save states rather than a training run.
    """

    @property
    def baseline(self) -> Path:
        """
        Locates the JSON file holding the random baseline's `Evaluation`
        under the run's evaluation seeds, which the run's first evaluation
        writes.
        """
        return self.directory / "baseline.json"

    @property
    def baselined(self) -> Evaluation | None:
        """
        Reads the random baseline's evaluation `baseline` holds, or `None`
        where the run has played none.
        """
        return Evaluation.model_validate_json(
            self.baseline.read_bytes()
        ) if self.baseline.exists() else None

    @property
    def checkpoint(self) -> Path:
        """
        Locates the checkpoint a run writes at each interval and at its end,
        which a resumed run continues training from.
        """
        return self.directory / "checkpoint.npz"

    @property
    def demonstration(self) -> Recording:
        """
        Reads the recording of the shortest episode `episodes` holds that
        started in Blue's bedroom and reached the run's goal, the first of
        those sharing its length.

        Raises:
            ValueError: Where `episodes` holds none.
        """
        reached = (
            episode for episode in self.recorded
            if episode.terminated and episode.recording.takeover is None
        )

        if shortest := min(reached, default=None, key=attrgetter("length")):
            return shortest.recording

        raise ValueError(
            f"{self.episodes} holds no episode reaching "
            f"{self.settings.environment.goal.name} from the bedroom"
        )

    @property
    def directory(self) -> Path:
        """
        Locates the directory holding everything the run writes, the one
        `read` read it from, or otherwise the one under `data/runs/` its
        name gives.
        """
        return self._read_from or self.folder / self.name

    @property
    def episodes(self) -> Path:
        """
        Locates the JSON Lines file holding one `Episode` per line, in the
        order the run played them.
        """
        return self.directory / "episodes.jsonl"

    @property
    def evaluated(self) -> Iterator[Evaluation]:
        """
        Reads each evaluation of the agent `evaluations` holds, in the order
        the run played them, validating each line only once a caller draws
        its evaluation.
        """
        return map(Evaluation.model_validate_json, self.lines(self.evaluations))

    @property
    def evaluations(self) -> Path:
        """
        Locates the JSON Lines file holding one `Evaluation` of the agent
        per line, in the order the run played them.
        """
        return self.directory / "evaluations.jsonl"

    @property
    def iterations(self) -> Path:
        """
        Locates the JSON Lines file holding one `Iteration` of a search per
        line, in the order the search ran them.
        """
        return self.directory / "iterations.jsonl"

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
        digest of its start, the instant it started, and the run it resumes.
        """
        return self.directory / self.file

    @property
    def recorded(self) -> Iterator[Episode]:
        """
        Reads each episode `episodes` holds, in the order the run played
        them, validating each line only once a caller draws its episode.
        """
        return map(Episode.model_validate_json, self.lines(self.episodes))

    @property
    def stop(self) -> Path:
        """
        Locates the file whose presence stops the run where its loop next
        pauses, the end of an episode for the deep Q-network, the end of a
        rollout's update for PQN and PPO, and the end of an iteration for a
        search, which `squirtl stop` writes.
        """
        return self.directory / "stop"

    def append(self, path: Path, *records: Record):
        """
        Appends each of `records` to `path`, one of the run's JSON Lines
        files, as a line of JSON apiece, first cutting with a warning the
        unfinished last line a run that stopped while writing it leaves,
        which every reader skips.
        """
        with path.open("a+b") as lines:
            if (end := lines.seek(0, SEEK_END)) and pread(
                lines.fileno(),
                1,
                end - 1
            ) != b"\n":
                logger.warning("Cutting the unfinished last line of {}", path)
                lines.seek(0)
                lines.truncate(lines.read().rfind(b"\n") + 1)

            lines.writelines(
                f"{record.model_dump_json()}\n".encode() for record in records
            )

    def carry(self, lines: Iterable[str], path: Path):
        """
        Writes `lines`, each a line the stopped run a resume continues wrote
        to the file of the same name, into `path`, one of this run's JSON
        Lines files, as the stopped run wrote them, so a resumed run's file
        opens on the lines it carries over.
        """
        path.write_text("".join(lines), encoding="utf-8")

    def check(self, digest: str):
        """
        Refuses `digest`, the digest of the state a console's intro left,
        where it differs from the one the run recorded, as it does on a
        cartridge other than the one the run trained on.

        Raises:
            ValueError: Where the two differ.
        """
        if digest != self.digest:
            raise ValueError(
                f"{self.directory} recorded the intro leaving the console in a state "
                f"of digest {self.digest}, where this cartridge leaves {digest}"
            )

    def check_episodes(self):
        """
        Reads each line of `episodes` through `Episode`, as `episode` reads
        the line `squirtl watch` plays, refusing the run at the first line
        that does not parse, such as one written before a field of the
        record was renamed.

        Raises:
            ValueError: Where a line does not parse, naming `episodes`, the
                        line's number counting from 1, and each field it
                        fails at.
        """
        for number, line in enumerate(self.lines(self.episodes), 1):
            try:
                Episode.model_validate_json(line)
            except ValidationError as error:
                raise ValueError(
                    f"Line {number:,} of {self.episodes} holds no episode, failing "
                    + ", ".join(failures(error))
                ) from error

    def check_files(self):
        """
        Refuses a run whose directory holds no `episodes`, or a run that
        trained an agent whose directory holds no `checkpoint`, the files a
        run writes as it trains or searches.

        Raises:
            FileNotFoundError: Where one is missing, naming the run's
                               directory and the file it lacks.
        """
        for path in (self.episodes,) if self.searches else (
            self.checkpoint, self.episodes
        ):
            if not path.is_file():
                raise FileNotFoundError(f"{self.directory} holds no {path.name}")

    def check_trained(self):
        """
        Refuses a run that searched rather than trained an agent.

        Raises:
            ValueError: Where the run is a search, naming the commands that
                        read one.
        """
        if self.searches:
            raise ValueError(
                f"{self.directory} holds a search, which `squirtl watch` plays and "
                f"`squirtl search --resume` continues"
            )

    def ended_by(self, step: int) -> list[str]:
        """
        Reads the line of each episode `episodes` holds that ended by `step`
        of the run, meaning each whose steps and the steps before it total
        no more, validating no line and reading only its `length`. It reads
        no line past the episode ending on `step`.

        Raises:
            ValueError: Where those episodes total fewer steps than `step`
                        while `step` falls short of the run's `steps`,
                        as where a crash lost the log's last lines, since
                        only the checkpoint at a run's end lands within
                        an episode.
        """
        ended = []
        taken = 0

        for line in self.lines(self.episodes):
            length = loads(line)["length"]

            if taken + length > step:
                break

            ended.append(line)
            taken += length

            if taken == step:
                return ended

        if step < self.settings.steps:
            raise ValueError(
                f"{self.episodes} ends its episodes at step {taken:,}, short of the "
                f"checkpoint at step {step:,}"
            )

        return ended

    def episode(self, number: int | None = None) -> Episode:
        """
        Reads episode `number` of `episodes`, counting from 1, or the last
        where `number` is `None`, validating that line alone.

        Raises:
            IndexError: Where `episodes` holds no such episode.
        """
        if found := deque(
            islice(self.lines(self.episodes), number and number - 1, number),
            maxlen = 1
        ):
            return Episode.model_validate_json(found[0])

        raise IndexError(f"{self.episodes} holds no episode {number or 'at all'}")

    def evaluated_by(self, step: int) -> Iterator[Evaluation]:
        """
        Reads each evaluation `evaluations` holds of the agent at `step` of
        the run or before it, in the order the run played them.
        """
        return takewhile(lambda evaluation: evaluation.step <= step, self.evaluated)

    def first(self, count: int, path: Path | None = None) -> list[str]:
        """
        Reads the first `count` lines of `path`, one of the run's JSON Lines
        files, or of `episodes` where it is `None`, validating no line.

        Raises:
            ValueError: Where the file holds fewer, as where a crash lost
                        the log's last lines.
        """
        path = path or self.episodes

        if len(lines := list(islice(self.lines(path), count))) < count:
            raise ValueError(
                f"{path} holds {len(lines):,} lines, short of the {count:,} the "
                f"checkpoint follows"
            )

        return lines

    def lines(self, path: Path) -> Iterator[str]:
        """
        Reads each line of `path`, one of the run's JSON Lines files, as the
        text it holds, in the order the lines run, and none where the run
        holds no such file. It skips with a warning a last line lacking its
        newline, as a run that stopped while writing it leaves it.
        """
        if path.exists():
            with path.open(encoding="utf-8") as lines:
                for line in lines:
                    if line.endswith("\n"):
                        yield line
                    else:
                        logger.warning("Skipping the unfinished last line of {}", path)

    @classmethod
    def read(cls, directory: Path) -> Self:
        """
        Reads the run whose record `directory` holds, every path of which
        then sits in `directory`, whatever the working directory.

        Raises:
            FileNotFoundError : Where `directory` holds no record.
            ValidationError   : Where the record holds no run.
        """
        run = cls.model_validate_json(
            (directory / cls.file).read_text(encoding="utf-8")
        )
        run._read_from = directory

        return run

    @classmethod
    def start(
        cls,
        digest   : str,
        settings : RunSettings,
        started  : datetime,
        resumes  : str | None = None,
        searches : bool       = False
    ) -> Self:
        """
        Creates the directory of a run reading `settings` from `started` on
        and writes its record there, holding those settings, that instant,
        the revision of the clone in the working directory, and `digest`.

        Args:
            digest   : The SHA-256 digest of the state `GameBoy.start` left
                       the run's console in.
            resumes  : The name of the run this one continues, or `None` for
                       a run starting afresh.
            searches : Whether the run is a search over save states.

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
            digest   = digest,
            resumes  = resumes,
            revision = Revision.checked_out(),
            searches = searches,
            settings = settings,
            started  = started
        )
        run.directory.mkdir(parents=True)
        run.record.write_text(run.model_dump_json(indent=2), encoding="utf-8")

        return run

    def sync(self, path: Path):
        """
        Writes `path`, one of the run's files, through to disk, so nothing
        saved after it runs ahead of what it holds.
        """
        with path.open("ab") as file:
            flush(file.fileno())


class RunListing(Record):
    """
    The settings naming one run among others, its agent, whether it trained
    along the curriculum, and its seed, beside its name.
    """

    agent: Algorithm
    """
    The agent the run trained.
    """

    curriculum: bool
    """
    Whether the run started its training episodes along a demonstration.
    """

    name: str
    """
    The run's name, the folder holding it.
    """

    seed: int
    """
    The seed the run's random draws derive from.
    """

    @property
    def start(self) -> Start:
        """
        Names where the run's training episodes start.
        """
        return Start.CURRICULUM if self.curriculum else Start.BEDROOM

    @classmethod
    def of(cls, run: Run, **fields: object) -> Self:
        """
        Reads the listing of `run` from the settings it recorded, beside the
        further `fields` a subclass declares.
        """
        return cls(
            agent      = run.settings.agent.algorithm,
            curriculum = run.settings.curriculum.demonstration is not None,
            name       = run.name,
            seed       = run.settings.seed,
            **fields
        )


class Episode(Outcome):
    """
    One episode as a run records it on a line of its `episodes`, from what
    the episode reached to the `Recording` that `squirtl watch` plays back,
    beside the measures of the agent that played it.
    """

    epsilon: float | None
    """
    The chance of a random action at the episode's last step, or `None` for
    PPO, which samples each action from its policy.
    """

    recording: Recording
    """
    The `timer_div` and the presses the emulator plays the episode back
    from.
    """

    update: PolicyUpdate | Update | None
    """
    Each measure of the agent's updates averaged over those taken while the
    episode played, the loss and the value for the deep Q-network and PQN
    and PPO's own for PPO, or `None` where none ran.
    """
