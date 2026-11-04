"""
Pins the file the agent writes at each checkpoint, covering:

- A checkpoint reading back as written with each `state_dict`'s metadata
  and replay memory's arrays, refusing a file holding more than tensors
  and plain values or a network entry that is no tensor
- The `.npz` a checkpoint is written as, each member compressed with zstd,
  the checkpoint an interrupted write leaves as it was, the partial file a
  killed one leaves, a file cut short or holding a damaged zstd frame,
  which it refuses naming it, and the archive a save flushes whole before
  the directory
- The weights read from a checkpoint's `agent.pt` member alone
"""

from collections.abc import Callable
from numpy           import load as load_npz, zeros
from numpy.testing   import assert_array_equal
from os              import fstat, truncate
from pathlib         import Path
from pickle          import UnpicklingError
from pydantic        import ValidationError
from pytest          import MonkeyPatch, mark, param, raises
from stat            import S_ISDIR
from torch           import arange, equal, save, tensor, uint8
from torch.nn        import Linear
from zipfile         import ZIP_ZSTANDARD, ZipFile

from squirtl.agent.checkpoint import Checkpoint, Weights


def blank(**fields: object) -> Checkpoint:
    """
    Builds a checkpoint holding nothing at step 0, any keyword setting a
    field in its place.
    """
    return Checkpoint(
        **{
            "step"        : 0,
            "exploration" : {},
            "online"      : {},
            "optimizer"   : {},
            "replay"      : {},
            "sampling"    : {},
            "target"      : {}
        }
        | fields
    )


def cut_in_half(path: Path):
    """
    Cuts the file at `path` to its first half.
    """
    truncate(path, path.stat().st_size // 2)


def cut_to_nothing(path: Path):
    """
    Cuts the file at `path` to no bytes at all.
    """
    truncate(path, 0)


def flip_agent_frame(path: Path):
    """
    Flips the first byte of the zstd frame the `agent.pt` member of the
    archive at `path` holds, its local header taking 30 bytes beside the
    member's name.
    """
    with ZipFile(path) as archive:
        member = archive.getinfo("agent.pt")

    data = bytearray(path.read_bytes())
    data[member.header_offset + 30 + len(member.filename)] ^= 0xFF
    path.write_bytes(data)


def mark_an_unknown_method(path: Path):
    """
    Writes into the central directory entry of the archive's first member at
    `path` a compression method `zipfile` supports none of, at the 10 bytes
    past that entry's signature where the method sits.
    """
    data    = bytearray(path.read_bytes())
    central = data.index(b"PK\x01\x02")
    data[central + 10 : central + 12] = b"\xff\x00"
    path.write_bytes(data)


def misname_agent(path: Path):
    """
    Changes the last letter of the `agent.pt` member's name in both of the
    archive's headers at `path`, as damage to those bytes reads.
    """
    path.write_bytes(path.read_bytes().replace(b"agent.pt", b"agent.pX"))


def pack(agent: dict[str, object], path: Path, **members: bytes):
    """
    Writes an `.npz` holding `agent` as its `agent.pt` member, the way
    `Checkpoint.save` writes every field but `replay`, beside each of
    `members` under its name.
    """
    with ZipFile(path, "w") as archive:
        with archive.open("agent.pt", "w") as member:
            save(agent, member)

        for name, data in members.items():
            archive.writestr(name, data)


def test_a_checkpoint_is_an_npz_whose_members_zstd_compresses(tmp_path: Path):
    """
    Asserts that a checkpoint's file is an `.npz` NumPy's own `load` reads
    replay memory's arrays from, beside the `agent.pt` member, with every
    member compressed with zstd.
    """
    blank(replay={"actions": zeros(4, "int64"), "held": zeros(4, bool)}).save(
        tmp_path / "checkpoint.npz"
    )

    with load_npz(tmp_path / "checkpoint.npz") as archive:
        assert (sorted(archive.files), archive["held"].dtype) == (
            ["actions", "agent.pt", "held"],
            bool
        )
        assert {member.compress_type for member in archive.zip.infolist()} == {
            ZIP_ZSTANDARD
        }


@mark.parametrize(
    "network",
    [param("online", id="the-online-network"), param("target", id="the-target-network")]
)
def test_a_checkpoint_refuses_a_network_entry_that_is_no_tensor(
    network  : str,
    tmp_path : Path
):
    """
    Asserts that reading a checkpoint refuses a file whose online or target
    network holds a list where a tensor goes, naming that entry.
    """
    pack(
        agent = {
            "step"        : 0,
            "exploration" : {},
            "online"      : {},
            "optimizer"   : {},
            "sampling"    : {},
            "target"      : {}
        }
        | {network: {"weight": [1.0, 2.0]}},
        path = tmp_path / "checkpoint.npz"
    )

    with raises(ValidationError, match=rf"{network}\.weight"):
        Checkpoint.from_path(tmp_path / "checkpoint.npz")


def test_a_checkpoint_keeps_the_metadata_each_state_dict_carries(tmp_path: Path):
    """
    Asserts that a checkpoint holds each network's `state_dict` itself, and
    that one read back from its file still carries the `_metadata` holding
    each module's version, which `load_state_dict` reads.
    """
    online, target = Linear(2, 1).state_dict(), Linear(2, 1).state_dict()
    written        = blank(online=online, target=target)
    written.save(tmp_path / "checkpoint.npz")
    read = Checkpoint.from_path(tmp_path / "checkpoint.npz")

    assert written.online is online and written.target is target
    assert (read.online._metadata, read.target._metadata) == (
        {"": {"version": 1}},
        {"": {"version": 1}}
    )


def test_a_checkpoint_reads_back_as_the_one_written(tmp_path: Path):
    """
    Asserts that a checkpoint written to a file reads back with every field
    equal to the one written, each array of replay memory in its own dtype.
    """
    written = blank(
        exploration = {"bit_generator": "PCG64", "state": {"inc": 1, "state": 2**100}},
        online      = {"weight": tensor([1.0, 2.0])},
        optimizer   = {"param_groups": [{"lr": 1e-4, "params": [0]}], "state": {}},
        replay      = {"frames": arange(24, dtype=uint8).reshape(2, 3, 4).numpy()},
        sampling    = {"bit_generator": "PCG64", "state": {"inc": 5, "state": 3}},
        step        = 12,
        target      = {"weight": tensor([0.5, 2.0])}
    )
    written.save(tmp_path / "checkpoint.npz")
    read = Checkpoint.from_path(tmp_path / "checkpoint.npz")

    assert equal(read.online["weight"], written.online["weight"])
    assert equal(read.target["weight"], written.target["weight"])
    assert_array_equal(read.replay["frames"], written.replay["frames"], strict=True)
    assert (read.exploration, read.optimizer, read.sampling, read.step) == (
        written.exploration, written.optimizer, written.sampling, written.step
    )


def test_a_checkpoint_refuses_a_file_holding_an_arbitrary_object(tmp_path: Path):
    """
    Asserts that reading a checkpoint refuses a file whose `agent.pt` member
    holds an object beyond tensors and plain values, which `torch.load`'s
    default `weights_only=True` unpickles alone.
    """
    pack({"online": Path("online.pt")}, tmp_path / "checkpoint.npz")

    with raises(UnpicklingError, match="Weights only load failed"):
        Checkpoint.from_path(tmp_path / "checkpoint.npz")


def test_a_save_flushes_the_whole_archive_then_the_directory_it_lands_in(
    monkeypatch : MonkeyPatch,
    tmp_path    : Path
):
    """
    Asserts that a save flushes the `.partial` file through the drive's
    cache once the archive's end record is written, the file then taking the
    checkpoint's path with no byte past what was flushed, and then flushes
    the directory the checkpoint lands in.
    """
    flushed     = []
    directories = []
    monkeypatch.setattr(
        "squirtl.agent.checkpoint.flush",
        lambda descriptor: flushed.append(
            (fstat(descriptor).st_ino, fstat(descriptor).st_size)
        )
    )
    monkeypatch.setattr(
        "squirtl.agent.checkpoint.fsync",
        lambda descriptor: directories.append(S_ISDIR(fstat(descriptor).st_mode))
    )
    path = tmp_path / "checkpoint.npz"
    blank(replay={"actions": zeros(4, "int64")}, step=3).save(path)

    assert (flushed, directories) == (
        [(path.stat().st_ino, path.stat().st_size)],
        [True]
    )


def test_a_save_writes_over_the_partial_file_a_killed_save_left(tmp_path: Path):
    """
    Asserts that a save beside the `.partial` file a killed save left behind
    writes over it and leaves the checkpoint alone in its directory.
    """
    (tmp_path / "checkpoint.npz.partial").write_bytes(b"left by a killed save")
    blank().save(tmp_path / "checkpoint.npz")

    assert [path.name for path in tmp_path.iterdir()] == ["checkpoint.npz"]


@mark.parametrize(
    "damage",
    [
        param(cut_to_nothing,   id="an-empty-file"),
        param(cut_in_half,      id="its-first-half"),
        param(flip_agent_frame, id="a-damaged-zstd-frame"),
        param(misname_agent,          id="a-damaged-member-name"),
        param(mark_an_unknown_method, id="a-damaged-compression-method")
    ]
)
def test_a_damaged_checkpoint_is_refused_naming_its_file(
    damage   : Callable[[Path], None],
    tmp_path : Path
):
    """
    Asserts that reading a checkpoint whose file holds nothing, its
    first half alone, a damaged zstd frame, or a zip header damaged in a
    member's name or its compression method, which raise `KeyError` and
    `NotImplementedError`, raises `ValueError` naming the file, the error
    the commands refuse.
    """
    path = tmp_path / "checkpoint.npz"
    blank(replay={"actions": zeros(64, "int64")}, step=3).save(path)
    damage(path)

    with raises(ValueError, match=f"{path} holds no whole checkpoint"):
        Checkpoint.from_path(path)


def test_a_write_interrupted_partway_leaves_the_last_checkpoint_as_it_was(
    monkeypatch : MonkeyPatch,
    tmp_path    : Path
):
    """
    Asserts that an interrupt landing while a checkpoint writes replay
    memory's arrays leaves the checkpoint at its path as the last write left
    it, and no partial file beside it.
    """
    checkpoint = blank(replay={"actions": zeros(4, "int64")}, step=3)
    checkpoint.save(tmp_path / "checkpoint.npz")
    written = (tmp_path / "checkpoint.npz").read_bytes()

    def interrupt(*_: object):
        """
        Stands in for an interrupt landing during the write of an array.
        """
        raise KeyboardInterrupt

    monkeypatch.setattr("squirtl.agent.checkpoint.save_npy", interrupt)

    with raises(KeyboardInterrupt):
        checkpoint.model_copy(update={"step": 4}).save(tmp_path / "checkpoint.npz")

    assert [path.name for path in tmp_path.iterdir()] == ["checkpoint.npz"]
    assert (tmp_path / "checkpoint.npz").read_bytes() == written


def test_weights_read_the_agent_member_alone_leaving_replay_memory_unread(
    tmp_path: Path
):
    """
    Asserts that `Weights` reads the online network and the step from a
    checkpoint's `agent.pt` member alone, even where a member of replay
    memory holds an array header cut short, which `Checkpoint` refuses to
    read.
    """
    agent = {
        "step"        : 12,
        "online"      : {"weight": tensor([1.0, 2.0])},
        "exploration" : {},
        "optimizer"   : {},
        "sampling"    : {},
        "target"      : {}
    }

    pack(agent, tmp_path / "checkpoint.npz", **{"actions.npy": b"\x93NUMPY\x01\x00"})

    weights = Weights.from_path(tmp_path / "checkpoint.npz")

    assert (weights.online["weight"].tolist(), weights.step) == ([1.0, 2.0], 12)

    with raises(ValueError):
        Checkpoint.from_path(tmp_path / "checkpoint.npz")
