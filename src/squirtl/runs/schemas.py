"""
Defines the records one run reads and writes:

- `RunSettings`, every setting the run reads
- `Revision`, the code the run ran on
- `Run`, the directory under `data/runs/` recording both, each episode, each
  evaluation, and the checkpoint
- `Episode`, one episode as a line of the run's `episodes`
- `Stream`, the streams of random draws the run makes
"""

from collections     import deque
from collections.abc import Iterator
from datetime        import UTC, datetime
from enum            import StrEnum, auto
from hashlib         import sha256
from itertools       import islice, takewhile
from json            import loads
from loguru          import logger
from numpy           import uint64
from numpy.random    import SeedSequence
from os              import SEEK_END, pread
from pathlib         import Path
from pydantic        import AwareDatetime, Field, NonNegativeInt, PositiveInt, PrivateAttr, StringConstraints
from subprocess      import check_output
from typing          import Annotated, Self

from squirtl.agent.schemas       import AgentSettings, PolicyUpdate, Update, flush
from squirtl.emulator.schemas    import EmulatorSettings, Record
from squirtl.environment.schemas import EnvironmentSettings, Outcome, Recording
from squirtl.evaluation.schemas  import Evaluation, EvaluationSettings
from squirtl.reward.schemas      import RewardSettings

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
    The environment steps between checkpoints, each written at the first
    episode end, or the end of a rollout's update for PQN and PPO, reaching
    a multiple of them, whose default is the 250,000 steps of each iteration
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

    evaluation: EvaluationSettings = Field(default_factory=EvaluationSettings)
    """
    The settings each evaluation of the agent reads.
    """

    evaluation_steps: PositiveInt = 250_000
    """
    The environment steps between the evaluations a run plays, each where
    an episode end, the end of a rollout's update for PQN and PPO, or the
    run's last step first reaches a multiple of them, whose default is the
    250,000 steps of each iteration Dopamine's DQN evaluates after.
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

    steps: PositiveInt = 2_500_000
    """
    The environment steps the run takes, a run of PQN or PPO going on to
    the end of the rollout that reaches them, whose default is ten of the
    250,000-step iterations Dopamine's DQN evaluates after.
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

    @property
    def baseline(self) -> Path:
        """
        Locates the JSON file holding the random baseline's `Evaluation`
        under the run's evaluation seeds, which the run's first evaluation
        writes.
        """
        return self.directory / "baseline.json"

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
        Locates the directory holding everything the run writes, the one
        `read` read it from, or otherwise the one under `data/runs/` its
        name gives.
        """
        return self._read_from or Path("data/runs", self.name)

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
        return self.directory / "run.json"

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
        Locates the file whose presence stops the run where its training
        loop next pauses, the end of an episode for the deep Q-network and
        the end of a rollout's update for PQN and PPO, which `squirtl stop`
        writes.
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

    def first(self, count: int) -> list[str]:
        """
        Reads the line of each of the first `count` episodes `episodes`
        holds, validating no line.

        Raises:
            ValueError: Where `episodes` holds fewer, as where a crash lost
                        the log's last lines.
        """
        if len(lines := list(islice(self.lines(self.episodes), count))) < count:
            raise ValueError(
                f"{self.episodes} holds {len(lines):,} episodes, short of the "
                f"{count:,} the checkpoint follows"
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
            (directory / "run.json").read_text(encoding="utf-8")
        )
        run._read_from = directory

        return run

    @classmethod
    def start(
        cls,
        digest   : str,
        settings : RunSettings,
        started  : datetime,
        resumes  : str | None = None
    ) -> Self:
        """
        Creates the directory of a run reading `settings` from `started` on
        and writes its record there, holding those settings, that instant,
        the revision of the clone in the working directory, and `digest`.

        Args:
            digest  : The SHA-256 digest of the state `GameBoy.start` left
                      the run's console in.
            resumes : The name of the run this one continues, or `None` for
                      a run starting afresh.

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
