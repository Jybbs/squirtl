"""
Pins the file a stopped search continues from, covering:

- A checkpoint reading back as the one written, whose members `zipfile`
  compresses and whose networks read onto the CPU
- A cut-short or damaged file refused naming it
- A write leaving no `.partial` file beside the checkpoint
- The same checkpoint writing the same bytes whatever date the
  environment sets
"""

from collections.abc import Callable
from common.search   import assert_same_checkpoint, ending
from pathlib         import Path
from pytest          import MonkeyPatch, fixture, mark, param, raises
from zipfile         import ZIP_ZSTANDARD, ZipFile

from squirtl.search.checkpoint import SearchCheckpoint
from squirtl.search.particles  import Search


@fixture
def checkpoint(
    rolled    : Callable[..., object],
    searching : Callable[..., Search]
) -> SearchCheckpoint:
    """
    Builds the checkpoint of a search that has played one outer step of its
    first group.
    """
    search = searching(rolled([ending(x=1), ending(x=2), ending(x=3), ending(x=4)]))

    search.step(search.groups)

    return search.checkpoint


@fixture
def saved(checkpoint: SearchCheckpoint, tmp_path: Path) -> Path:
    """
    Writes `checkpoint` to `checkpoint.npz` under `tmp_path`.

    Returns:
        The file's path.
    """
    path = tmp_path / "checkpoint.npz"

    checkpoint.save(path)

    return path


def test_a_checkpoint_is_an_npz_whose_members_zstd_compresses(
    checkpoint : SearchCheckpoint,
    saved      : Path
):
    """
    Asserts that every member of the file, the frontier and the networks
    beside each array, is compressed through zstd.
    """
    with ZipFile(saved) as archive:
        members = archive.infolist()

    assert {member.filename for member in members} == {
        "frontier.json",
        "networks.pt",
        *(f"{name}.npy" for name in checkpoint.arrays)
    }
    assert {member.compress_type for member in members} == {ZIP_ZSTANDARD}


def test_a_checkpoint_reads_back_as_the_one_written(
    checkpoint : SearchCheckpoint,
    saved      : Path
):
    """
    Asserts that the checkpoint a file holds reads back with the same
    frontier, the same arrays bit for bit, and the same networks.
    """
    assert_same_checkpoint(SearchCheckpoint.from_path(saved), checkpoint)


def test_a_checkpoint_writes_the_same_bytes_whatever_the_date(
    checkpoint  : SearchCheckpoint,
    monkeypatch : MonkeyPatch,
    tmp_path    : Path
):
    """
    Asserts that the checkpoint written under two values of
    `SOURCE_DATE_EPOCH`, which dates a member `ZipFile.writestr` adds, holds
    the same bytes both times.
    """
    written = []

    for epoch in ("1000000000", "2000000000"):
        monkeypatch.setenv("SOURCE_DATE_EPOCH", epoch)

        checkpoint.save(path := tmp_path / f"{epoch}.npz")

        written.append(path.read_bytes())

    assert written[0] == written[1]


def test_a_write_leaves_no_partial_file(saved: Path):
    """
    Asserts that a written checkpoint sits alone in its directory.
    """
    assert [*saved.parent.iterdir()] == [saved]


@mark.parametrize(
    "damage",
    [
        param(lambda data: data[:len(data) // 2], id="cut-in-half"),
        param(lambda data: b"",                   id="cut-to-nothing")
    ]
)
def test_a_damaged_checkpoint_is_refused_naming_its_file(
    damage : Callable[[bytes], bytes],
    saved  : Path
):
    """
    Asserts that a file cut short raises `ValueError` naming it.
    """
    saved.write_bytes(damage(saved.read_bytes()))

    with raises(ValueError, match=saved.name):
        SearchCheckpoint.from_path(saved)
