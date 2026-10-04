"""
Pins the records one run reads and writes, covering:

- The settings refusing a change once built
- The seed each stream derives from the run's one seed
- The revision read from a clone, and what marks it dirty
- The directory a run creates under `data/runs/`, the record it writes
  there, and the run a resumed one names
"""

from dataclasses      import FrozenInstanceError, asdict
from datetime         import UTC, datetime, timedelta, timezone
from hashlib          import sha256
from json             import loads
from pathlib          import Path
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
        param(-1,    id="negative"),
        param(2**64, id="past-64-bits")
    ]
)
def test_each_stream_starts_from_a_seed_of_its_own(seed: int):
    """
    Asserts that no two streams of one run start from the same seed,
    whatever integer the run's seed is, since each stream's name
    personalizes the hash its seed comes from.
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


def test_a_revision_outside_a_clone_raises_the_error_git_exits_with(
    monkeypatch : MonkeyPatch,
    tmp_path    : Path
):
    """
    Asserts that reading a revision where no clone holds the working
    directory raises the error git exits with, rather than recording a run
    with no commit. `GIT_CEILING_DIRECTORIES` stops git looking for a clone
    above the directory the test owns.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))

    with raises(CalledProcessError):
        Revision.checked_out()


def test_a_run_outside_a_clone_raises_before_writing_anything(
    monkeypatch : MonkeyPatch,
    tmp_path    : Path
):
    """
    Asserts that starting a run where no clone holds the working directory
    raises the error git exits with before creating any directory, since the
    run reads its revision first.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))

    with raises(CalledProcessError):
        Run.start(RunSettings(), datetime(2026, 10, 4, tzinfo=UTC))

    assert not (tmp_path / "data").exists()


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
        "revision" : asdict(Revision.checked_out()),
        "started"  : "2026-10-04T12:30:05.123456+00:00",
        "settings" : {"seed": 7}
    }


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


def test_adjacent_run_seeds_share_no_stream_seed():
    """
    Asserts that runs taking adjacent seeds start no stream from the same
    seed, the pair a seed derived by adding an offset per stream would
    collide on.
    """
    assert not (
        set(RunSettings(seed=1).seeds.values())
        & set(RunSettings(seed=2).seeds.values())
    )


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


@mark.parametrize(
    "started",
    [
        param(datetime(2026, 10, 4, 12, 30, 5, 123456, tzinfo=UTC), id="in-utc"),
        param(
            datetime(2026, 10, 4, 22, tzinfo=timezone(timedelta(hours=-5))),
            id = "behind-utc-across-midnight"
        ),
        param(
            datetime(
                2026,
                10,
                4,
                1,
                15,
                tzinfo = timezone(timedelta(hours=5, minutes=30))
            ),
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


def test_the_settings_refuse_a_change_once_built():
    """
    Asserts that a built `RunSettings` raises on an assignment, so no step
    of a run moves a setting another step has already read.
    """
    with raises(FrozenInstanceError):
        RunSettings().seed = 2
