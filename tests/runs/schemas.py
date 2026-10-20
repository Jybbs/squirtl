"""
Pins the records one run reads and writes, covering:

- Each record refusing a change once built and a key no field declares,
  from the run down to each subject's settings, and the settings refusing
  a negative seed
- The default, the bounds, and the description each field of the settings
  declares, the run's own and each subject's
- The seed each stream derives from the run's one seed
- The revision read from a clone, what marks it dirty, and the output it
  refuses
- The directory a run creates under `data/runs/`, the record it writes
  there, and the run a resumed one names
- The paths a run keeps in its directory, a run read back from it or from
  a copy outside the clone, a directory holding no run, and the episodes a
  run's `episodes` holds, each line read only once drawn, an unfinished
  last line skipped with a warning, and one episode read by validating its
  line alone
- The lines of the episodes ending by a checkpoint, and a log ending short
  of a checkpoint below the run's steps, which is refused
- The evaluations a run plays where it lacks them and reads where it holds
  them, under its evaluation stream's seed, and a run holding none
"""

from collections.abc   import Callable, Mapping
from common.evaluation import EvaluatorStandIn, played
from datetime          import UTC, datetime
from functools         import reduce
from hashlib           import sha256
from json              import dumps, loads
from operator          import getitem
from os                import fstat
from pathlib           import Path
from pydantic          import ValidationError
from pytest            import MonkeyPatch, TempPathFactory, mark, param, raises
from shutil            import copytree
from subprocess        import CalledProcessError, check_output
from syrupy.assertion  import SnapshotAssertion

from squirtl.agent.schemas      import Weights
from squirtl.emulator.schemas   import Cartridge, Record
from squirtl.evaluation.schemas import Evaluation
from squirtl.runs.schemas       import Episode, Revision, Run, RunSettings, Stream


def test_a_checkpoint_at_the_runs_last_step_may_land_within_an_episode(
    episode : Episode,
    holding : Callable[[str], Run]
):
    """
    Asserts that a run of 6 steps reads, at its last step, the line of the
    three-step episode that ended by it, the four-step one after it cut
    short by the run's end.
    """
    run  = holding(f"{episode.model_dump_json()}\n")
    last = run.model_copy(update={"settings": RunSettings(steps=6)})

    assert last.ended_by(6) == [f"{episode.model_dump_json()}\n"]


@mark.parametrize(
    "seed",
    [
        param(1,     id="the-default"),
        param(0,     id="zero"),
        param(2**64, id="past-64-bits")
    ]
)
def test_each_stream_starts_from_a_seed_of_its_own(seed: int):
    """
    Asserts that no two streams of one run start from the same seed,
    whatever non-negative integer the run's seed is, since each stream takes
    a child of its own from the run seed's `SeedSequence`.
    """
    assert len(set(RunSettings(seed=seed).seeds.values())) == len(Stream)


def test_a_clean_clone_reads_as_its_commit_and_its_lockfile(clone: Path):
    """
    Asserts that the revision of an unchanged clone names the commit git
    logs for it, carries the SHA-256 digest of its `uv.lock`, and is not
    dirty.
    """
    assert Revision.checked_out() == Revision(
        commit   = check_output(["git", "log", "-1", "--format=%H"], text=True).strip(),
        dirty    = False,
        lockfile = sha256(b"version = 1\n").hexdigest()
    )


def test_a_resumed_run_names_the_run_it_continues(clone: Path):
    """
    Asserts that a run resuming another records the name of the run it
    continues in a directory of its own.
    """
    resumed = Run.start(
        "0",
        RunSettings(),
        datetime(2026, 10, 5, tzinfo=UTC),
        Run.start("0", RunSettings(), datetime(2026, 10, 4, tzinfo=UTC)).name
    )

    assert loads(resumed.record.read_text(encoding="utf-8"))["resumes"] == (
        "20261004T000000.000000Z"
    )


def test_a_revision_outside_a_clone_raises_the_error_git_exits_with(outside: Path):
    """
    Asserts that reading a revision where no clone holds the working
    directory raises the error git exits with, rather than recording a run
    with no commit.
    """
    with raises(CalledProcessError):
        Revision.checked_out()


def test_a_run_holding_no_evaluations_reads_none(run: Run):
    """
    Asserts that a run whose directory holds no `evaluations`, as a run that
    has played none leaves it, reads no evaluation rather than raising.
    """
    assert list(run.evaluated) == []


@mark.usefixtures("clone")
@mark.parametrize(
    ("path", "dirty"),
    [
        param("notes.md",           True,  id="an-untracked-file"),
        param("uv.lock",            True,  id="a-changed-tracked-file"),
        param("data/runs/run.json", False, id="a-file-under-data")
    ]
)
def test_a_revision_is_dirty_wherever_git_reports_a_change(
    checkout : Callable[[Mapping[str, str]], None],
    dirty    : bool,
    path     : str
):
    """
    Asserts that an untracked file and a change to a tracked one each mark
    the revision dirty, whereas a file under `data/`, which `.gitignore`
    covers and which holds everything a run writes, leaves it clean.
    """
    checkout({path: "changed\n"})

    assert Revision.checked_out().dirty is dirty


def test_a_run_outside_a_clone_raises_before_writing_anything(outside: Path):
    """
    Asserts that starting a run where no clone holds the working directory
    raises the error git exits with before creating any directory, since the
    run reads its revision first.
    """
    with raises(CalledProcessError):
        Run.start("0", RunSettings(), datetime(2026, 10, 4, tzinfo=UTC))

    assert not (outside / "data").exists()


def test_a_run_reads_an_episode_validating_its_line_alone(
    episode : Episode,
    holding : Callable[[str], Run]
):
    """
    Asserts that a run reads its second episode though the line before it
    holds no episode, since it validates the line it returns alone.
    """
    run = holding(f'{{"length": 3}}\n{episode.model_dump_json()}\n')

    assert run.episode(2) == episode


@mark.parametrize(
    ("first", "second"),
    [
        param(1,  2,     id="adjacent"),
        param(0,  2**64, id="apart-by-2-to-the-64")
    ]
)
def test_distinct_run_seeds_share_no_stream_seed(first: int, second: int):
    """
    Asserts that runs taking distinct seeds start no stream from the same
    seed, covering the adjacent pair an offset per stream would collide on
    and the pair a 64-bit mask on the run seed would.
    """
    assert set(RunSettings(seed=first).seeds.values()).isdisjoint(
        RunSettings(seed=second).seeds.values()
    )


def test_a_run_reads_back_from_its_directory_as_the_run_that_started(clone: Path):
    """
    Asserts that reading the directory a run started in returns that run,
    whether the directory is named relative to the working directory or
    absolutely, each read keeping its paths in the directory it names.
    """
    run = Run.start("0", RunSettings(seed=7), datetime(2026, 10, 4, tzinfo=UTC))

    assert [
        (read.model_dump(), read.directory)
        for read in map(Run.read, (run.directory, clone / run.directory))
    ] == [
        (run.model_dump(), run.directory),
        (run.model_dump(), clone / run.directory)
    ]


def test_a_run_record_reads_back_as_the_run_that_wrote_it(clone: Path):
    """
    Asserts that the JSON a run writes into its directory validates back
    into a record equal to the run that wrote it.
    """
    run = Run.start("0", RunSettings(seed=7), datetime(2026, 10, 4, tzinfo=UTC))

    assert Run.model_validate_json(run.record.read_text(encoding="utf-8")) == run


@mark.parametrize(
    "started",
    [
        param(datetime.fromisoformat("2026-10-04T12:30:05.123456Z"), id="in-utc"),
        param(
            datetime.fromisoformat("2026-10-04T22:00-05:00"),
            id = "behind-utc-across-midnight"
        ),
        param(
            datetime.fromisoformat("2026-10-04T01:15+05:30"),
            id = "ahead-of-utc-across-midnight"
        )
    ]
)
def test_a_run_name_reads_back_as_the_instant_it_started(
    revision : Revision,
    started  : datetime
):
    """
    Asserts that `datetime.fromisoformat` reads the name of a run back as
    the instant the run started, whether that instant carries UTC or an
    offset that moves its date in UTC.
    """
    name = Run(
        digest   = "0",
        revision = revision,
        settings = RunSettings(),
        started  = started
    ).name

    assert datetime.fromisoformat(name) == started


def test_a_run_records_its_settings_revision_and_start(clone: Path):
    """
    Asserts that a run writes its record into the directory named for the
    instant it started under `data/runs/`, holding the digest of its start,
    its settings, the revision of the clone, that instant, and no run it
    resumes.
    """
    settings = RunSettings(seed=7)
    Run.start("0", settings, datetime(2026, 10, 4, 12, 30, 5, 123456, tzinfo=UTC))

    assert loads(
        (clone / "data/runs/20261004T123005.123456Z/run.json").read_text(
            encoding = "utf-8"
        )
    ) == {
        "digest"   : "0",
        "resumes"  : None,
        "revision" : Revision.checked_out().model_dump(),
        "started"  : "2026-10-04T12:30:05.123456Z",
        "settings" : settings.model_dump(mode="json")
    }


def test_a_run_refuses_an_instant_with_no_offset(revision: Revision):
    """
    Asserts that a run built on an instant carrying no UTC offset raises
    rather than reading that instant as the machine's local time.
    """
    with raises(ValidationError, match="timezone info"):
        Run(revision=revision, settings=RunSettings(), started=datetime(2026, 10, 4))


@mark.usefixtures("clone")
def test_an_untracked_file_marks_a_revision_dirty_whatever_git_config_hides(
    checkout    : Callable[[Mapping[str, str]], None],
    monkeypatch : MonkeyPatch
):
    """
    Asserts that an untracked file marks the revision dirty in a clone whose
    configuration sets `status.showUntrackedFiles` to `no`.
    """
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "status.showUntrackedFiles")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "no")
    checkout({"notes.md": "changed\n"})

    assert Revision.checked_out().dirty


def test_a_run_skips_an_unfinished_last_line_with_a_warning(
    episode : Episode,
    holding : Callable[[str], Run],
    logged  : list[str]
):
    """
    Asserts that a run reads its episodes past a last line lacking its
    newline, as a run that stopped while writing it leaves it, logging a
    warning naming the file rather than failing to validate the line.
    """
    run = holding(f'{episode.model_dump_json()}\n{{"length": ')

    assert (list(run.recorded), logged) == (
        [episode],
        [f"Skipping the unfinished last line of {run.episodes}"]
    )


@mark.parametrize(
    "commit",
    [
        param("fatal: not a git repository", id="an-error-message"),
        param("",                            id="nothing-at-all")
    ]
)
def test_a_revision_refuses_output_that_holds_no_hash(commit: str):
    """
    Asserts that a commit that is empty or holds any character other than a
    lowercase hexadecimal digit is refused.
    """
    with raises(ValidationError):
        Revision(commit=commit, dirty=False, lockfile="0")


def test_a_run_started_at_the_instant_of_another_leaves_it_as_it_was(clone: Path):
    """
    Asserts that a run started at the same instant as an earlier one raises
    rather than writing into the earlier run's directory, whose record stays
    as the earlier run wrote it.
    """
    started = datetime(2026, 10, 4, tzinfo=UTC)
    first   = Run.start("0", RunSettings(seed=1), started)
    record  = first.record.read_text(encoding="utf-8")

    with raises(FileExistsError):
        Run.start("0", RunSettings(seed=2), started)

    assert first.record.read_text(encoding="utf-8") == record


@mark.parametrize(
    ("path", "field", "value"),
    [
        param((), "started", datetime(2026, 10, 5, tzinfo=UTC), id="the-run"),
        param(("revision",),            "dirty",       True, id="the-revision"),
        param(("settings",),            "seed",        2,    id="the-settings"),
        param(("settings", "agent"),    "batch_size",  64,   id="the-agent-settings"),
        param(
            ("settings", "emulator"),
            "open_window",
            True,
            id = "the-emulator-settings"
        ),
        param(
            ("settings", "environment"),
            "frames_per_step",
            24,
            id = "the-environment-settings"
        ),
        param(("settings", "reward"),   "novelty",     0.01, id="the-reward-settings")
    ]
)
def test_a_record_refuses_a_change_once_built(
    field : str,
    path  : tuple[str, ...],
    run   : Run,
    value : object
):
    """
    Asserts that a run, its revision, its settings, and each subject's
    settings they hold each raise on an assignment once built, so no step
    moves a setting another step has read and a run's directory and record
    stay where its start put them.
    """
    with raises(ValidationError, match="frozen"):
        setattr(reduce(getattr, path, run), field, value)


@mark.parametrize(
    "path",
    [
        param((),            id="the-run"),
        param(("revision",), id="the-revision"),
        param(("settings",), id="the-settings"),
        *(
            param(("settings", subject), id=f"the-{subject}-settings")
            for subject, value in RunSettings()
            if isinstance(value, Record)
        )
    ]
)
def test_a_run_record_refuses_a_key_no_field_declares(path: tuple[str, ...], run: Run):
    """
    Asserts that a run record carrying a key no field declares, at its top
    level or inside its revision, its settings, or a subject's settings they
    hold, is refused rather than read back with the key dropped.
    """
    record = run.model_dump()
    reduce(getitem, path, record)["sead"] = 7

    with raises(ValidationError, match="Extra inputs are not permitted"):
        Run.model_validate(record)


@mark.parametrize(
    ("path", "name"),
    [
        param(Run.baseline,    "baseline.json",     id="the-baseline"),
        param(Run.checkpoint,  "checkpoint.npz",    id="the-checkpoint"),
        param(Run.episodes,    "episodes.jsonl",    id="the-episodes"),
        param(Run.evaluations, "evaluations.jsonl", id="the-evaluations"),
        param(Run.stop,        "stop",              id="the-stop-file")
    ]
)
def test_each_file_a_run_writes_sits_in_its_directory(
    name : str,
    path : property,
    run  : Run
):
    """
    Asserts that the baseline, the checkpoint, the episodes, the
    evaluations, and the stop file a run keeps each sit in its directory
    under the name a reader finds it by.
    """
    assert path.fget(run) == run.directory / name


@mark.usefixtures("clone")
def test_a_run_read_from_outside_the_clone_keeps_its_files_where_it_was_read(
    monkeypatch      : MonkeyPatch,
    tmp_path_factory : TempPathFactory
):
    """
    Asserts that a copy of a run's directory outside the clone, read from a
    working directory there, holds the run that started and keeps each file
    of the run in that copy.
    """
    run  = Run.start("0", RunSettings(), datetime(2026, 10, 4, tzinfo=UTC))
    copy = copytree(run.directory, tmp_path_factory.mktemp("shell") / run.name)
    monkeypatch.chdir(copy.parent)
    copied = Run.read(copy)

    assert copied.model_dump() == run.model_dump()
    assert [copied.checkpoint, copied.episodes, copied.record, copied.stop] == [
        copy / name for name in ("checkpoint.npz", "episodes.jsonl", "run.json", "stop")
    ]


def test_a_run_writes_nothing_outside_its_own_directory(clone: Path):
    """
    Asserts that starting a run creates its directory under `data/runs/` and
    the record inside it, and creates or removes no other file or directory
    outside the clone's own git metadata.
    """
    changed  = set(clone.rglob("*"))
    run      = Run.start("0", RunSettings(), datetime(2026, 10, 4, tzinfo=UTC))
    changed ^= set(clone.rglob("*"))

    assert {
        path.relative_to(clone) for path in changed if ".git" not in path.parts
    } == {Path("data"), Path("data/runs"), run.directory, run.record}


def test_a_runs_episodes_read_back_in_the_order_written(
    episode : Episode,
    holding : Callable[[str], Run]
):
    """
    Asserts that a run reads each line of its `episodes` back as the episode
    written there, nested recording included, in the order the lines run,
    and parses no line past the last one drawn, so a line a stopped run left
    half written stays unread.
    """
    later    = episode.model_copy(update={"length": 4})
    recorded = holding(
        f'{episode.model_dump_json()}\n{later.model_dump_json()}\n{{"length": '
    ).recorded

    assert [next(recorded), next(recorded)] == [episode, later]


def test_a_sync_writes_the_file_through_the_drives_cache(
    monkeypatch : MonkeyPatch,
    run         : Run,
    tmp_path    : Path
):
    """
    Asserts that syncing one of a run's files hands `flush` a descriptor of
    that file, which writes it through the drive's cache.
    """
    flushed = []
    monkeypatch.setattr(
        "squirtl.runs.schemas.flush",
        lambda descriptor: flushed.append(fstat(descriptor).st_ino)
    )
    path = tmp_path / "episodes.jsonl"
    path.write_text("", encoding="utf-8")
    run.sync(path)

    assert flushed == [path.stat().st_ino]


@mark.parametrize(
    ("number", "length"),
    [
        param(1, 3, id="the-first"),
        param(2, 4, id="the-second"),
        param(None, 4, id="the-last")
    ]
)
def test_a_run_reads_the_episode_its_number_names_or_its_last(
    episode : Episode,
    holding : Callable[[str], Run],
    length  : int,
    number  : int | None
):
    """
    Asserts that a run reads the episode a number counting from 1 names, and
    its last where no number is given.
    """
    run = holding(
        f"{episode.model_dump_json()}\n"
        f"{episode.model_copy(update={'length': 4}).model_dump_json()}\n"
    )

    assert run.episode(number).length == length


@mark.parametrize(
    "number",
    [param(3, id="past-the-last"), param(None, id="the-last-of-none")]
)
def test_a_run_holding_no_such_episode_raises_naming_its_episodes(
    holding : Callable[[str], Run],
    number  : int | None
):
    """
    Asserts that asking a run for an episode past the ones it recorded, or
    for the last of none, raises `IndexError` naming the file it read.
    """
    with raises(IndexError, match="episodes.jsonl holds no episode"):
        holding("").episode(number)


@mark.parametrize(
    ("step", "ended"),
    [param(3, 1, id="as-the-first-ends"), param(7, 2, id="as-the-second-ends")]
)
def test_a_run_reads_the_lines_of_the_episodes_that_ended_by_a_step(
    ended   : int,
    episode : Episode,
    holding : Callable[[str], Run],
    logged  : list[str],
    step    : int
):
    """
    Asserts that a run reads, as written, the line of each episode ending
    by a step from its `length` alone, a three-step episode's once that step
    reaches 3 and the four-step one's after it once it reaches 7, and reads
    no further, so the unfinished line past them draws no warning.
    """
    lines = ['{"length": 3}\n', '{"length": 4}\n']
    run   = holding(f'{lines[0]}{lines[1]}{{"length": ')

    assert (run.ended_by(step), logged) == (lines[:ended], [])


@mark.parametrize(
    "step",
    [param(2, id="before-the-first-ends"), param(6, id="a-step-short-of-the-second")]
)
def test_a_log_ending_short_of_a_checkpoint_within_the_run_is_refused(
    episode : Episode,
    holding : Callable[[str], Run],
    step    : int
):
    """
    Asserts that a run whose episodes end short of a checkpoint below its
    `steps` refuses to read them, since only the checkpoint at a run's end
    lands within an episode.
    """
    run = holding(
        f"{episode.model_dump_json()}\n"
        f"{episode.model_copy(update={'length': 4}).model_dump_json()}\n"
    )

    with raises(ValueError, match=f"short of the checkpoint at step {step}"):
        run.ended_by(step)


def test_an_append_cuts_the_unfinished_last_line_before_writing(
    logged   : list[str],
    run      : Run,
    tmp_path : Path
):
    """
    Asserts that appending an evaluation to a file whose last line a run
    that stopped while writing it left unfinished cuts that line, with a
    warning naming the file, so the file reads back as the evaluation it
    held before and the one appended.
    """
    path = tmp_path / "evaluations.jsonl"
    path.write_text(
        f'{played([0.1], 12).model_dump_json()}\n{{"outco',
        encoding = "utf-8"
    )
    run.append(path, played([0.2], 20))

    assert (
        [evaluation.step for evaluation in map(
            Evaluation.model_validate_json,
            (
                path.read_text(encoding="utf-8")
                    .splitlines()
            )
        )],
        logged
    ) == ([12, 20], [f"Cutting the unfinished last line of {path}"])


def test_each_stream_seed_fits_in_64_unsigned_bits():
    """
    Asserts that every stream's seed is a 64-bit unsigned integer, the
    widest seed `torch.manual_seed` takes.
    """
    assert all(0 <= value < 2**64 for value in RunSettings().seeds.values())


@mark.usefixtures("clone")
def test_a_run_plays_the_evaluations_it_lacks_and_reads_those_it_holds(
    cartridge  : Cartridge,
    evaluators : list[EvaluatorStandIn]
):
    """
    Asserts that a run's first evaluation, at step 10, plays the agent and
    the baseline under the run's evaluation stream and settings and writes
    both, that a second at step 10 reads both back without starting an
    evaluator, and that one at step 20 plays the agent alone, reading the
    baseline the run holds.
    """
    run    = Run.start("0", RunSettings(), datetime(2026, 10, 4, tzinfo=UTC))
    played = [
        run.evaluate(cartridge, Weights(online={}, step=step)) for step in (10, 10, 20)
    ]

    assert [stand_in.asked for stand_in in evaluators] == [[10, None], [20]]
    assert evaluators[0].arguments == (
        run.settings.agent.device,
        run.settings.seeds[Stream.EVALUATION],
        run.settings.evaluation,
        run.settings.specification(cartridge)
    )
    assert (played[1], played[2][1]) == (played[0], played[0][1])
    assert [evaluation.step for evaluation in run.evaluated] == [10, 20]


@mark.usefixtures("clone")
def test_a_run_holding_its_evaluation_but_no_baseline_plays_the_baseline_alone(
    cartridge  : Cartridge,
    evaluators : list[EvaluatorStandIn]
):
    """
    Asserts that a run holding the agent's evaluation at step 10 but no
    baseline, as a resume from a run that wrote none leaves it, plays the
    baseline alone and writes it.
    """
    run = Run.start("0", RunSettings(), datetime(2026, 10, 4, tzinfo=UTC))
    run.append(run.evaluations, played([0.01], 10))
    run.evaluate(cartridge, Weights(online={}, step=10))

    assert ([stand_in.asked for stand_in in evaluators], run.baseline.exists()) == (
        [[None]],
        True
    )


def test_reading_a_directory_holding_no_run_raises(clone: Path):
    """
    Asserts that reading a directory holding no run record raises rather
    than reading a run from somewhere else.
    """
    (clone / "data/runs/empty").mkdir(parents=True)

    with raises(FileNotFoundError):
        Run.read(clone / "data/runs/empty")


def test_the_default_seed_derives_the_stream_seeds_its_fixture_holds(
    snapshot: SnapshotAssertion
):
    """
    Asserts that the default run seed derives the stream seeds its fixture
    file holds, so a change to the derivation, which would change the draws
    every recorded run's seed reproduces, is reviewed as a diff.
    """
    seeds = RunSettings().seeds

    assert "\n".join(f"{stream} {seed}" for stream, seed in seeds.items()) == snapshot


def test_the_settings_carry_the_defaults_and_descriptions_their_fixture_holds(
    snapshot: SnapshotAssertion
):
    """
    Asserts that the run's settings, and each subject's settings they
    hold, carry the default and the bounds each field declares beside the
    description written beneath it, which cyclopts renders as the help of
    that field's flag, so a change to any of them is reviewed as a diff.
    """
    assert dumps(
        RunSettings.model_json_schema(),
        ensure_ascii = False,
        indent       = 2
    ) == snapshot


def test_the_settings_refuse_a_negative_seed():
    """
    Asserts that a negative seed is refused, since `SeedSequence` takes a
    non-negative integer as its entropy.
    """
    with raises(ValidationError, match="greater than or equal to 0"):
        RunSettings(seed=-1)
