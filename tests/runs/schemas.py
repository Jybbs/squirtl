"""
Pins the records one run reads and writes, covering:

- The settings refusing a change once built and a negative seed
- The seed each stream derives from the run's one seed
- The revision read from a clone, what marks it dirty, and the output it
  refuses
- The directory a run creates under `data/runs/`, the record it writes
  there, and the run a resumed one names
"""

from datetime         import UTC, datetime
from hashlib          import sha256
from json             import loads
from pathlib          import Path
from pydantic         import ValidationError
from pytest           import MonkeyPatch, mark, param, raises
from subprocess       import CalledProcessError, check_output
from syrupy.assertion import SnapshotAssertion

from squirtl.runs.schemas import Revision, Run, RunSettings, Stream


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


def test_a_resumed_run_names_the_run_it_continues(clone: Path):
    """
    Asserts that a run resuming another records the name of the run it
    continues in a directory of its own.
    """
    first   = Run.start(RunSettings(), datetime(2026, 10, 4, tzinfo=UTC))
    resumed = Run.start(RunSettings(), datetime(2026, 10, 5, tzinfo=UTC), first.name)

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


def test_a_run_outside_a_clone_raises_before_writing_anything(outside: Path):
    """
    Asserts that starting a run where no clone holds the working directory
    raises the error git exits with before creating any directory, since the
    run reads its revision first.
    """
    with raises(CalledProcessError):
        Run.start(RunSettings(), datetime(2026, 10, 4, tzinfo=UTC))

    assert not (outside / "data").exists()


def test_a_run_record_reads_back_as_the_run_that_wrote_it(clone: Path):
    """
    Asserts that the JSON a run writes into its directory validates back
    into a record equal to the run that wrote it.
    """
    run = Run.start(RunSettings(seed=7), datetime(2026, 10, 4, tzinfo=UTC))

    assert Run.model_validate_json(run.record.read_text(encoding="utf-8")) == run


@mark.parametrize(
    ("path", "dirty"),
    [
        param("notes.md",           True,  id="an-untracked-file"),
        param("uv.lock",            True,  id="a-changed-tracked-file"),
        param("data/runs/run.json", False, id="a-file-under-data")
    ]
)
def test_a_revision_is_dirty_wherever_git_reports_a_change(
    clone : Path,
    dirty : bool,
    path  : str
):
    """
    Asserts that an untracked file and a change to a tracked one each mark
    the revision dirty, whereas a file under `data/`, which `.gitignore`
    covers and which holds everything a run writes, leaves it clean.
    """
    written = clone / path
    written.parent.mkdir(exist_ok=True, parents=True)
    written.write_text("changed\n", encoding="utf-8")

    assert Revision.checked_out().dirty is dirty


def test_a_run_records_its_settings_revision_and_start(clone: Path):
    """
    Asserts that a run writes its record into the directory named for
    the instant it started under `data/runs/`, holding its settings, the
    revision of the clone, that instant, and no run it resumes.
    """
    Run.start(RunSettings(seed=7), datetime(2026, 10, 4, 12, 30, 5, 123456, tzinfo=UTC))

    assert loads(
        (clone / "data/runs/20261004T123005.123456Z/run.json").read_text(
            encoding = "utf-8"
        )
    ) == {
        "resumes"  : None,
        "revision" : Revision.checked_out().model_dump(),
        "started"  : "2026-10-04T12:30:05.123456Z",
        "settings" : {"seed": 7}
    }


def test_a_run_refuses_an_instant_with_no_offset():
    """
    Asserts that a run built on an instant carrying no UTC offset raises
    rather than reading that instant as the machine's local time.
    """
    with raises(ValidationError, match="timezone info"):
        Run(
            revision = Revision(commit="0", dirty=False, lockfile="0"),
            settings = RunSettings(),
            started  = datetime(2026, 10, 4)
        )


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
    assert not (
        set(RunSettings(seed=first).seeds.values())
        & set(RunSettings(seed=second).seeds.values())
    )


def test_a_run_started_at_the_instant_of_another_leaves_it_as_it_was(clone: Path):
    """
    Asserts that a run started at the same instant as an earlier one raises
    rather than writing into the earlier run's directory, whose record stays
    as the earlier run wrote it.
    """
    started = datetime(2026, 10, 4, tzinfo=UTC)
    first   = Run.start(RunSettings(seed=1), started)
    record  = first.record.read_text(encoding="utf-8")

    with raises(FileExistsError):
        Run.start(RunSettings(seed=2), started)

    assert first.record.read_text(encoding="utf-8") == record


def test_a_run_writes_nothing_outside_its_own_directory(clone: Path):
    """
    Asserts that starting a run creates its directory under `data/runs/` and
    the record inside it, and creates or removes no other file or directory
    outside the clone's own git metadata.
    """
    changed  = set(clone.rglob("*"))
    run      = Run.start(RunSettings(), datetime(2026, 10, 4, tzinfo=UTC))
    changed ^= set(clone.rglob("*"))

    assert {
        path.relative_to(clone) for path in changed if ".git" not in path.parts
    } == {Path("data"), Path("data/runs"), run.directory, run.record}


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
def test_a_run_name_reads_back_as_the_instant_it_started(started: datetime):
    """
    Asserts that `datetime.fromisoformat` reads the name of a run back as
    the instant the run started, whether that instant carries UTC or an
    offset that moves its date in UTC.
    """
    run = Run(
        revision = Revision(commit="0", dirty=False, lockfile="0"),
        settings = RunSettings(),
        started  = started
    )

    assert datetime.fromisoformat(run.name) == started


def test_an_untracked_file_marks_a_revision_dirty_whatever_git_config_hides(
    clone       : Path,
    monkeypatch : MonkeyPatch
):
    """
    Asserts that an untracked file marks the revision dirty in a clone whose
    configuration sets `status.showUntrackedFiles` to `no`.
    """
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "status.showUntrackedFiles")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "no")
    (clone / "notes.md").write_text("changed\n", encoding="utf-8")

    assert Revision.checked_out().dirty


def test_each_stream_seed_fits_in_64_unsigned_bits():
    """
    Asserts that every stream's seed is a 64-bit unsigned integer, the
    widest seed `torch.manual_seed` takes.
    """
    assert all(0 <= value < 2**64 for value in RunSettings().seeds.values())


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


def test_the_seed_carries_the_description_written_beneath_it():
    """
    Asserts that `seed` carries the docstring written beneath it as its
    description, which cyclopts renders as the help of `--seed`.
    """
    assert RunSettings.model_fields["seed"].description == (
        "The seed every random draw in the run derives from, whose default\n"
        "follows CleanRL's `dqn_atari.py`."
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
    Asserts that a commit holding anything but hexadecimal digits is
    refused, so no record carries a commit that is not a hexadecimal hash.
    """
    with raises(ValidationError):
        Revision(commit=commit, dirty=False, lockfile="0")


def test_the_settings_refuse_a_negative_seed():
    """
    Asserts that a negative seed is refused, since `SeedSequence` takes a
    non-negative integer as its entropy.
    """
    with raises(ValidationError, match="greater than or equal to 0"):
        RunSettings(seed=-1)


@mark.parametrize(
    ("record", "field", "value"),
    [
        param(RunSettings(), "seed", 2, id="the-settings"),
        param(
            Revision(commit="0", dirty=False, lockfile="0"),
            "dirty",
            True,
            id = "the-revision"
        ),
        param(
            Run(
                revision = Revision(commit="0", dirty=False, lockfile="0"),
                settings = RunSettings(),
                started  = datetime(2026, 10, 4, tzinfo=UTC)
            ),
            "started",
            datetime(2026, 10, 5, tzinfo=UTC),
            id = "the-run"
        )
    ]
)
def test_a_record_refuses_a_change_once_built(
    field  : str,
    record : Revision | Run | RunSettings,
    value  : object
):
    """
    Asserts that each record a run reads or writes raises on an assignment
    once built, so no step moves a setting another step has read and a run's
    directory and record stay where its start put them.
    """
    with raises(ValidationError, match="frozen"):
        setattr(record, field, value)


@mark.parametrize(
    "field",
    [
        param(None,       id="the-run"),
        param("revision", id="the-revision"),
        param("settings", id="the-settings")
    ]
)
def test_a_run_record_refuses_a_key_no_field_declares(field: str | None):
    """
    Asserts that a run record carrying a key no field declares, at its top
    level or inside its revision or its settings, is refused rather than
    read back with the key dropped.
    """
    record = Run(
        revision = Revision(commit="0", dirty=False, lockfile="0"),
        settings = RunSettings(),
        started  = datetime(2026, 10, 4, tzinfo=UTC)
    ).model_dump()
    (record[field] if field else record)["sead"] = 7

    with raises(ValidationError, match="Extra inputs are not permitted"):
        Run.model_validate(record)
