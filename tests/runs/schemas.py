"""
Pins the records one run reads and writes, covering:

- Each record refusing a change once built and a key no field declares,
  from the run down to each subject's settings, and the settings refusing
  a negative seed
- The default, the bounds, and the description each field of the settings
  declares, the run's own and each subject's, and the defaults ending the
  warm-up inside an anneal outlasting a random walk to the starter
- The seed each stream derives from the run's one seed
- The revision read from a clone, what marks it dirty, and the output it
  refuses
- An append cutting an unfinished last line with a warning, and a sync
  handing `flush` the file it writes through
- The directory a run creates under `data/runs/`, the record it writes
  there, and the run a resumed one names
- The paths a run keeps in its directory, a run read back from it or from
  a copy outside the clone, a directory holding no run, and the episodes a
  run's `episodes` holds, each line read only once drawn, an unfinished
  last line skipped with a warning, and one episode read by validating its
  line alone
- The lines of the episodes ending by a checkpoint, and a log ending short
  of a checkpoint below the run's steps, which is refused
- The lines of the first episodes a checkpoint of PQN or PPO counts, and a
  log holding fewer, which is refused
- The measures and the epsilon of each agent's episode read back from its line
- A run holding no evaluations
- The demonstration a run's episodes give, the shortest reaching the starter
  from the bedroom, and a log holding none, which is refused
- The curriculum's settings refusing moves whose least passes their most and
  a required share above the completion share, and a run's settings refusing
  a demonstration for the deep Q-network and terms summing past 1 on the way
  to the run's goal
- A run refusing a digest other than the one it recorded, and the listing
  naming it among other runs
- A search refused where a trained run is read, and the search's stream
  coming after every other
- The defaults of `SearchSettings`, each from the column and the appendix of
  Mhammedi and Cohan's paper its docstring cites, the bound replay memory
  holds them to, the worker count following the machine, and a range
  running backward refused
"""

from collections.abc   import Callable, Mapping
from common.evaluation import played
from datetime          import UTC, datetime
from functools         import reduce
from hashlib           import sha256
from json              import dumps, loads
from operator          import getitem
from os                import fstat, process_cpu_count
from pathlib           import Path
from pydantic          import ValidationError
from pytest            import MonkeyPatch, TempPathFactory, mark, param, raises
from shutil            import copytree
from subprocess        import CalledProcessError, check_output
from syrupy.assertion  import SnapshotAssertion

from squirtl.agent.schemas       import AgentSettings, Algorithm, Measures, PolicyUpdate, Update
from squirtl.emulator.schemas    import Record
from squirtl.environment.schemas import EnvironmentSettings, Recording, Takeover
from squirtl.evaluation.schemas  import Evaluation
from squirtl.reward.schemas      import Event, RewardSettings
from squirtl.runs.schemas        import CurriculumSettings, Episode, Revision, Run, RunListing, RunSettings, Start
from squirtl.runs.schemas        import Stream
from squirtl.search.schemas      import SearchSettings


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


def test_a_log_holding_fewer_episodes_than_a_count_is_refused(
    holding: Callable[[str], Run]
):
    """
    Asserts that a run whose episodes hold fewer lines than a checkpoint of
    PQN or PPO counts refuses to read them, as where a crash lost its last
    lines.
    """
    run = holding('{"length": 3}\n')

    with raises(
        ValueError,
        match = "holds 1 lines, short of the 2 the checkpoint follows"
    ):
        run.first(2)


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


def test_a_run_holding_no_episode_reaching_its_goal_gives_no_demonstration(
    episode : Episode,
    holding : Callable[[str], Run]
):
    """
    Asserts that a run whose every episode truncated gives no demonstration,
    naming the goal its settings name, here the Pokédex rather than the
    default.
    """
    run = holding(f"{episode.model_dump_json()}\n").model_copy(
        update = {
            "settings": RunSettings(
                environment = EnvironmentSettings(goal=Event.EVENT_GOT_POKEDEX)
            )
        }
    )

    with raises(ValueError, match="holds no episode reaching EVENT_GOT_POKEDEX"):
        run.demonstration


def test_a_run_holding_no_evaluations_reads_none(run: Run):
    """
    Asserts that a run whose directory holds no `evaluations`, as a run that
    has played none leaves it, reads no evaluation rather than raising.
    """
    assert list(run.evaluated) == []


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


def test_a_run_reads_the_lines_of_its_first_episodes_reading_no_further(
    holding : Callable[[str], Run],
    logged  : list[str]
):
    """
    Asserts that a run reads, as written, the lines of the episodes a count
    names and reads no further, so the unfinished line past them draws no
    warning.
    """
    lines = ['{"length": 3}\n', '{"length": 4}\n']
    run   = holding(f'{lines[0]}{lines[1]}{{"length": ')

    assert (run.first(2), logged) == (lines, [])


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


def test_a_run_record_reads_back_as_the_run_that_wrote_it(clone: Path):
    """
    Asserts that the JSON a run writes into its directory validates back
    into a record equal to the run that wrote it.
    """
    run = Run.start("0", RunSettings(seed=7), datetime(2026, 10, 4, tzinfo=UTC))

    assert Run.model_validate_json(run.record.read_text(encoding="utf-8")) == run


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
        "searches" : False,
        "started"  : "2026-10-04T12:30:05.123456Z",
        "settings" : settings.model_dump(mode="json")
    }


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
def test_a_run_reads_its_baseline_only_once_it_has_played_one(run: Run):
    """
    Asserts that a run holding no baseline reads `None`, and that once its
    baseline is written it reads back the evaluation written.
    """
    assert run.baselined is None

    baseline = played([0.25], None)
    run.directory.mkdir(parents=True)
    run.baseline.write_text(baseline.model_dump_json(), encoding="utf-8")

    assert run.baselined == baseline


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


def test_a_run_refuses_an_instant_with_no_offset(revision: Revision):
    """
    Asserts that a run built on an instant carrying no UTC offset raises
    rather than reading that instant as the machine's local time.
    """
    with raises(ValidationError, match="timezone info"):
        Run(revision=revision, settings=RunSettings(), started=datetime(2026, 10, 4))


def test_a_run_refuses_another_digest_naming_both(run: Run):
    """
    Asserts that a run passes the digest it recorded and refuses any other,
    naming its directory, its own digest, and the one it was handed.
    """
    run.check("0")

    with raises(
        ValueError,
        match = f"{run.directory} .* digest 0, where this cartridge leaves 1"
    ):
        run.check("1")


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


@mark.parametrize(
    ("kept", "tail", "cut"),
    [
        param(1, "",        False, id="a-whole-last-line"),
        param(1, '{"outco', True,  id="an-unfinished-last-line"),
        param(0, "{",       True,  id="an-unfinished-line-alone")
    ]
)
def test_an_append_cuts_an_unfinished_last_line_alone(
    cut      : bool,
    kept     : int,
    logged   : list[str],
    run      : Run,
    tail     : str,
    tmp_path : Path
):
    """
    Asserts that appending an evaluation to a file whose last line a run
    that stopped while writing it left unfinished cuts that line, with a
    warning naming the file, and leaves a file ending on a whole line as
    it was, so the file reads back as the evaluations it held whole and the
    one appended.
    """
    path = tmp_path / "evaluations.jsonl"
    path.write_text(
        f"{played([0.1], 12).model_dump_json()}\n" * kept + tail,
        encoding = "utf-8"
    )
    run.append(path, played([0.2], 20))

    assert (
        [
            Evaluation.model_validate_json(line).step
            for line in path.read_text(encoding="utf-8").splitlines()
        ],
        logged
    ) == ([12] * kept + [20], [f"Cutting the unfinished last line of {path}"] * cut)


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


def test_a_runs_demonstration_is_its_shortest_episode_reaching_the_starter(
    episode : Episode,
    holding : Callable[[str], Run]
):
    """
    Asserts that a run's demonstration is the recording of the first of its
    shortest episodes reaching the starter from the bedroom, passing over a
    shorter one that truncated and a shorter one that took over from another
    demonstration.
    """
    lines = [
        episode.model_copy(update=fields) for fields in (
            {"length": 1},
            {
                "length"     : 3,
                "recording"  : Recording(presses=b"\x05", timer_div=1),
                "terminated" : True
            },
            {
                "length"     : 2,
                "recording"  : Recording(
                    presses  = b"\x05",
                    takeover = Takeover(
                        limit     = 9,
                        segment   = 0,
                        step      = 0,
                        timer_div = 0
                    ),
                    timer_div = 2
                ),
                "terminated" : True
            },
            {
                "length"     : 3,
                "recording"  : Recording(presses=b"\x06", timer_div=3),
                "terminated" : True
            }
        )
    ]
    run = holding("".join(f"{line.model_dump_json()}\n" for line in lines))

    assert run.demonstration == Recording(presses=b"\x05", timer_div=1)


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


def test_a_search_is_refused_where_a_trained_run_is_read(halted: Run):
    """
    Asserts that a search refuses to be read as a trained run, naming the
    commands that read one, while a training run reads as one.
    """
    with raises(ValueError, match="`squirtl watch` plays"):
        halted.check_trained()


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


def test_each_stream_seed_fits_in_64_unsigned_bits():
    """
    Asserts that every stream's seed is a 64-bit unsigned integer, the
    widest seed `torch.manual_seed` takes.
    """
    assert all(0 <= value < 2**64 for value in RunSettings().seeds.values())


def test_reading_a_directory_holding_no_run_raises(clone: Path):
    """
    Asserts that reading a directory holding no run record raises rather
    than reading a run from somewhere else.
    """
    (clone / "data/runs/empty").mkdir(parents=True)

    with raises(FileNotFoundError):
        Run.read(clone / "data/runs/empty")


@mark.parametrize(
    ("epsilon", "update"),
    [
        param(0.5,  None,                         id="no-update"),
        param(0.5,  Update(loss=1.0, value=-2.0), id="the-loss-and-the-value"),
        param(
            None,
            PolicyUpdate(
                clipped     = 0.25,
                entropy     = 1.5,
                kl          = 0.01,
                policy_loss = -0.5,
                value_loss  = 3.0
            ),
            id = "ppos-measures-at-no-epsilon"
        )
    ]
)
def test_an_episode_reads_back_the_measures_of_the_agent_that_played_it(
    episode : Episode,
    epsilon : float | None,
    update  : Measures | None
):
    """
    Asserts that an episode's line reads back into the record of measures it
    holds, `Update` or `PolicyUpdate`, at the epsilon it holds.
    """
    written = episode.model_copy(update={"epsilon": epsilon, "update": update})

    assert Episode.model_validate_json(written.model_dump_json()) == written


def test_the_default_capacity_holds_replay_memory_under_a_gigabyte():
    """
    Asserts that the default capacity, each slot one frame at the
    environment's default shape, holds fewer than a billion bytes.
    """
    height, width = EnvironmentSettings().frame_shape

    assert SearchSettings().capacity * height * width < 1_000_000_000


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


def test_the_default_warmup_ends_inside_an_anneal_outlasting_a_random_walk():
    """
    Asserts that at the default settings the chance of a random action
    anneals over at least the 37,000 presses a uniform random walk from the
    bedroom can take to reach the starter, and that the warm-up ends before
    that anneal does.
    """
    settings = RunSettings()
    anneal   = settings.agent.exploration_fraction * settings.steps

    assert settings.agent.warmup_steps < anneal and anneal >= 37_000


@mark.parametrize(
    ("goal", "past", "reward"),
    [
        param(
            Event.EVENT_GOT_STARTER,
            "0.21",
            RewardSettings(goal=0.31, milestone=0.3),
            id = "the-starter"
        ),
        param(
            Event.EVENT_GOT_STARTER,
            "2.22e-16",
            RewardSettings(goal=0.343, milestone=0.2, novelty=0.057),
            id = "by-the-rounding-of-a-share"
        ),
        param(
            Event.EVENT_GOT_POKEDEX,
            "0.25",
            RewardSettings(milestone=0.15),
            id = "the-pokedex"
        )
    ]
)
def test_the_settings_refuse_terms_one_step_could_sum_past_one_on_the_way_to_the_goal(
    goal   : Event,
    past   : str,
    reward : RewardSettings
):
    """
    Asserts that the settings refuse terms where a step reaching a new
    position and first setting every flag up to the run's goal at once earns
    past 1, naming the goal and how far past to three significant digits,
    whether the terms sum past 1 in decimal or sum to 1 in decimal and round
    past it once the milestone is counted three times.
    """
    with raises(
        ValidationError,
        match = f"every flag up to {goal.name} at once earns {past} more than the 1"
    ):
        RunSettings(environment=EnvironmentSettings(goal=goal), reward=reward)


@mark.parametrize(
    "reward",
    [
        param(
            RewardSettings(goal=0.5, milestone=0.125, novelty=0.125),
            id = "powers-of-two"
        ),
        param(RewardSettings(goal=0.68, milestone=0.07, novelty=0.11), id="decimals")
    ]
)
def test_the_settings_accept_terms_one_step_sums_to_exactly_one_at_the_goal(
    reward: RewardSettings
):
    """
    Asserts that the settings accept terms where a step reaching a new
    position and first setting every flag up to the starter at once earns
    exactly 1, the most the bound Mnih et al. clip each reward to allows.
    """
    assert RunSettings(reward=reward).reward == reward


@mark.parametrize(
    ("fields", "message"),
    [
        param({"back": (0.8, 0.5)}, r"back\n.*passes the most", id="back"),
        param({"forward": (1.5, 1.0)}, r"forward\n.*passes the most", id="forward"),
        param({"required": 0.96}, "passes the completion share", id="required")
    ]
)
def test_the_curriculums_settings_refuse_bounds_out_of_order(
    fields  : Mapping[str, object],
    message : str
):
    """
    Asserts that the curriculum's settings refuse a least move passing the
    most and a required share passing the completion share.
    """
    with raises(ValidationError, match=message):
        CurriculumSettings.model_validate(fields)


@mark.parametrize(
    "algorithm",
    [param(Algorithm.PPO, id="ppo"), param(Algorithm.PQN, id="pqn")]
)
def test_the_settings_take_a_demonstration_for_pqn_and_ppo(algorithm: Algorithm):
    """
    Asserts that the settings take a demonstration for PQN and PPO.
    """
    RunSettings(
        agent      = AgentSettings(algorithm=algorithm),
        curriculum = CurriculumSettings(demonstration=Path("data/runs/a"))
    )


def test_the_searchs_stream_leaves_the_seed_of_every_earlier_one_as_it_was():
    """
    Asserts that the search's stream comes last among the streams, since
    each stream's seed derives from its place, so every seed an earlier run
    drew from reads as it did.
    """
    assert [*Stream][-1] is Stream.SEARCH


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


@mark.parametrize(
    ("demonstration", "start"),
    [
        param(None,                Start.BEDROOM,    id="the-bedroom"),
        param(Path("data/runs/x"), Start.CURRICULUM, id="the-curriculum")
    ]
)
def test_a_listing_reads_the_settings_naming_its_run(
    demonstration : Path | None,
    run           : Run,
    start         : Start
):
    """
    Asserts that a run's listing holds its name, its agent, and its seed,
    and starts in the bedroom or along the curriculum as its settings name
    a demonstration.
    """
    listed = RunListing.of(
        run.model_copy(
            update = {
                "settings": RunSettings(
                    agent      = AgentSettings(algorithm=Algorithm.PPO),
                    curriculum = CurriculumSettings(demonstration=demonstration),
                    seed       = 4
                )
            }
        )
    )

    assert (listed.name, listed.agent, listed.seed, listed.start) == (
        run.name, Algorithm.PPO, 4, start
    )


def test_the_settings_count_no_flag_past_the_goal_toward_the_ceiling():
    """
    Asserts that terms summing past 1 over every flag up to the Pokédex are
    accepted for a run ending at the starter, whose episodes set none of the
    flags after it.
    """
    reward = RewardSettings(milestone=0.15)

    assert RunSettings(reward=reward).reward == reward


def test_the_settings_default_to_the_papers_montezuma_column():
    """
    Asserts that the population, the rollouts, the chance of a random press,
    and the predictor's settings default to the values the Montezuma's
    Revenge column of Table 5 and Appendices A.2 and A.3 of Mhammedi and
    Cohan's paper give them.
    """
    settings = SearchSettings()

    assert settings.model_dump(exclude={"capacity", "update_steps", "workers"}) == {
        "batch_size"    : 128,
        "epsilon"       : 0.2,
        "groups"        : 4,
        "learning_rate" : 3e-4,
        "particles"     : 32,
        "inner_steps"   : (5, 15),
        "outer_steps"   : (10, 20),
        "rollback"      : (1, 3)
    }


def test_the_settings_refuse_a_demonstration_for_the_deep_q_network():
    """
    Asserts that the settings refuse a demonstration beside the deep
    Q-network, which starts every episode in the bedroom.
    """
    with raises(ValidationError, match="takes no demonstration"):
        RunSettings(curriculum=CurriculumSettings(demonstration=Path("data/runs/a")))


def test_the_settings_refuse_a_negative_seed():
    """
    Asserts that a negative seed is refused, since `SeedSequence` takes a
    non-negative integer as its entropy.
    """
    with raises(ValidationError, match="greater than or equal to 0"):
        RunSettings(seed=-1)


def test_the_updates_default_to_the_ratio_of_the_papers_table():
    """
    Asserts that the presses between updates of the predictor default to the
    400 million frames of Mhammedi and Cohan's Table 6, four frames a press,
    over its 2.28 million updates, rounded.
    """
    assert SearchSettings().update_steps == round(400_000_000 / 4 / 2_280_000)


@mark.parametrize("field", ["inner_steps", "outer_steps", "rollback"])
def test_a_range_running_backward_is_refused(field: str):
    """
    Asserts that a range whose fewest exceeds its most raises, naming the
    field.
    """
    with raises(ValidationError, match=field):
        SearchSettings(**{field: (3, 2)})


@mark.parametrize("field", ["inner_steps", "outer_steps", "rollback"])
def test_a_range_of_one_value_is_accepted(field: str):
    """
    Asserts that a range whose fewest equals its most is accepted.
    """
    assert getattr(SearchSettings(**{field: (3, 3)}), field) == (3, 3)


def test_the_workers_default_to_the_cpus_the_process_may_use(monkeypatch: MonkeyPatch):
    """
    Asserts that the workers default to the count `process_cpu_count`
    reports, or to one where it reports none.
    """
    assert SearchSettings().workers == process_cpu_count()

    monkeypatch.setattr("squirtl.emulator.schemas.process_cpu_count", lambda: None)

    assert SearchSettings().workers == 1
