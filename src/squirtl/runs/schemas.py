"""
Defines the records one run reads and writes:

- `RunSettings`, every setting the run reads, `CurriculumSettings` among them
- `Revision`, the code the run ran on
- `Run`, the directory under `data/runs/` recording both, each episode, each
  evaluation, and the checkpoint
- `RunListing`, the settings naming a run among others, and `Start`, where
  its training episodes start
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
from operator        import attrgetter
from os              import SEEK_END, pread
from pathlib         import Path
from pydantic        import AwareDatetime, Field, NonNegativeFloat, NonNegativeInt, PositiveFloat, PositiveInt
from pydantic        import PrivateAttr, StringConstraints, ValidationError, model_validator
from subprocess      import check_output
from typing          import Annotated, ClassVar, Self

from squirtl.agent.schemas       import AgentSettings, Algorithm, PolicyUpdate, Update, flush
from squirtl.emulator.schemas    import EmulatorSettings, Record, UnitInterval
from squirtl.environment.schemas import EnvironmentSettings, Outcome, Recording
from squirtl.evaluation.schemas  import Evaluation, EvaluationSettings
from squirtl.reward.schemas      import RewardSettings

type Hexadecimal = Annotated[
    str, StringConstraints(pattern=r"^[0-9a-f]+$", strip_whitespace=True)
]


class CurriculumSettings(Record):
    """
    The settings of the curriculum that starts each training episode
    along a demonstration and moves the start back toward Blue's
    bedroom, each a field of `RunSettings.curriculum` and a key under
    `[tool.squirtl.curriculum]` in `pyproject.toml`. Every default but
    `demonstration` is the one Mhammedi and Cohan's Table 8 sets for the
    backward algorithm of their Appendix B.
    """

    back: tuple[PositiveFloat, PositiveFloat] = (0.25, 0.75)
    """
    The least and the most a window moves back, each a multiple of `window`,
    between which each move draws uniformly, whose default is the decrease
    multipliers of Mhammedi and Cohan's Table 8.
    """

    buffer: PositiveInt = 500
    """
    The steps an episode from a start takes beyond `multiplier` times the
    moving average of successful lengths before it truncates, whose default
    is the rollout length buffer of Mhammedi and Cohan's Table 8.
    """

    completion: UnitInterval = 0.95
    """
    The share of the recent episodes from a window reaching Blue's bedroom
    that have to succeed before its segment counts as solved, whose default
    is the completion threshold of Mhammedi and Cohan's Table 8.
    """

    demonstration: Path | None = None
    """
    The directory of the run whose shortest episode reaching the goal each
    training episode starts along, a run ending its episodes at the same
    goal, or `None` to start every episode in Blue's bedroom.
    """

    forward: tuple[PositiveFloat, PositiveFloat] = (0.5, 1.0)
    """
    The least and the most a window moves forward, each a multiple of
    `window`, between which each move draws uniformly, whose default is the
    increase multipliers of Mhammedi and Cohan's Table 8.
    """

    multiplier: PositiveFloat = 2.0
    """
    The multiple of the moving average of successful lengths an episode
    from a start takes before `buffer` and then truncates, whose default is
    the early termination multiplier of Mhammedi and Cohan's Table 8.
    """

    recent: PositiveInt = 32
    """
    The episodes from a window whose share of successes moves it, after
    which the count starts again, whose default is the minimum rollouts for
    an update of Mhammedi and Cohan's Table 8.
    """

    required: UnitInterval = 0.2
    """
    The share of the recent episodes from a window that have to succeed for
    it to move back, where a smaller share moves it forward, whose default
    is the required success rate of Mhammedi and Cohan's Table 8.
    """

    smoothing: UnitInterval = 0.9
    """
    The weight the moving average of successful lengths gives each new
    length, the smoothing constant of single exponential smoothing in
    section 6.4.3.1 of the NIST/SEMATECH e-Handbook of Statistical Methods,
    whose default is the smoothing factor of Mhammedi and Cohan's Table 8.
    """

    tolerance: NonNegativeFloat = 0.0
    """
    The reward an episode from a start may fall short of the
    demonstration's from the same step and still succeed, whose default is
    the failure reward tolerance of Mhammedi and Cohan's Table 8.
    """

    window: PositiveInt = 25
    """
    The steps of the demonstration each segment's window spans back from
    its latest start, whose default is the start delta window of Mhammedi
    and Cohan's Table 8.
    """

    @model_validator(mode="after")
    def verify(self) -> Self:
        """
        Refuses a `back` or a `forward` whose least move passes its most,
        and a `required` share above `completion`.

        Raises:
            ValueError: Where either holds, which Pydantic raises as a
                        `ValidationError`.
        """
        for name in ("back", "forward"):
            if (moves := getattr(self, name))[0] > moves[1]:
                raise ValueError(
                    f"the least {name} move of {moves[0]} passes the most of {moves[1]}"
                )

        if self.required > self.completion:
            raise ValueError(
                f"a required share of {self.required} passes the completion share "
                f"of {self.completion}"
            )

        return self


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
    WINDOW      = auto()


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

    machine: ClassVar[dict[str, set[str]]] = {
        "agent"      : {"device"},
        "evaluation" : {"environments"}
    }
    """
    The fields under each subject whose default follows the machine a run
    starts on, the agent's device and the environments an evaluation plays
    across, each left out of the defaults the site's pages state.
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

    curriculum: CurriculumSettings = Field(default_factory=CurriculumSettings)
    """
    The settings of the curriculum starting each training episode along a
    demonstration.
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

    @model_validator(mode="after")
    def verify(self) -> Self:
        """
        Refuses a demonstration for the deep Q-network, whose episodes start
        in Blue's bedroom alone, and reward settings whose ceiling at the
        environment's goal passes 1, the bound Mnih et al. clip each reward
        to.

        Raises:
            ValueError: Where either holds, which Pydantic raises as a
                        `ValidationError`.
        """
        if self.curriculum.demonstration and self.agent.algorithm is Algorithm.DQN:
            raise ValueError(
                f"the deep Q-network starts every episode in Blue's bedroom, so it "
                f"takes no demonstration such as {self.curriculum.demonstration}"
            )

        if (ceiling := self.reward.ceiling(goal := self.environment.goal)) > 1:
            raise ValueError(
                f"a step reaching a new position and every flag up to {goal.name} "
                f"at once earns {ceiling - 1:.3g} more than the 1 Mnih et al. clip "
                f"each reward to"
            )

        return self


class Run(Record):
    """
    One run, recorded in a directory of its own under `data/runs/` named for
    the instant it started.
    """

    folder: ClassVar[Path] = Path("data/runs")

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
                    + ", ".join(
                        f"at {'.'.join(map(str, problem['loc'])) or 'its root'} "
                        f"with {problem['msg']!r}"
                        for problem in error.errors(include_url=False)
                    )
                ) from error

    def check_files(self):
        """
        Refuses a run whose directory holds no `checkpoint` or no
        `episodes`, the files a run writes as it trains.

        Raises:
            FileNotFoundError: Where either is missing, naming the run's
                               directory and the file it lacks.
        """
        for path in (self.checkpoint, self.episodes):
            if not path.is_file():
                raise FileNotFoundError(f"{self.directory} holds no {path.name}")

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


class Start(StrEnum):
    """
    Where a run's training episodes start, in Blue's bedroom or along the
    demonstration its curriculum names.
    """

    BEDROOM    = auto()
    CURRICULUM = auto()


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
