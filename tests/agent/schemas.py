"""
Pins the records the agent reads and writes, covering:

- The device the settings default to, the values they refuse, and the
  bound a fraction accepts
- The value and the target a batch reads for each draw
- A checkpoint reading back as written with each `state_dict`'s metadata
  and replay memory's arrays, refusing a file holding more than tensors
  and plain values or a network entry that is no tensor
- The `.npz` a checkpoint is written as, each member compressed with zstd,
  the checkpoint an interrupted write leaves as it was, the partial file a
  killed one leaves, a file cut short, which it refuses naming it, and the
  flush that writes it through the drive's cache
- The weights read from a checkpoint's `agent.pt` member alone
"""

from numpy         import load as load_npz, zeros
from numpy.testing import assert_array_equal
from os            import truncate
from pathlib       import Path
from pickle        import UnpicklingError
from pydantic      import ValidationError
from pytest        import MonkeyPatch, mark, param, raises
from torch         import arange, device, equal, save, tensor, uint8
from torch.nn      import Linear
from zipfile       import ZIP_ZSTANDARD, ZipFile

from squirtl.agent.schemas       import AgentSettings, Batch, Checkpoint, Weights, flush
from squirtl.environment.schemas import Entry


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


@mark.parametrize(
    ("accelerator", "expected"),
    [
        param(device("mps"), "mps", id="an-accelerator"),
        param(None,          "cpu", id="no-accelerator")
    ]
)
def test_the_device_defaults_to_the_accelerator_torch_reports(
    accelerator : device | None,
    expected    : str,
    monkeypatch : MonkeyPatch
):
    """
    Asserts that the device defaults to the accelerator torch reports as
    available, and to the CPU where it reports none.
    """
    monkeypatch.setattr(
        "squirtl.agent.schemas.current_accelerator",
        lambda check_available: accelerator if check_available else device("cuda")
    )

    assert AgentSettings().device == expected


@mark.parametrize(
    ("field", "value"),
    [
        param("batch_size",           0,    id="no-transitions-per-batch"),
        param("capacity",             0,    id="no-frames-held"),
        param("discount",             0,    id="no-discount"),
        param("discount",             1.01, id="a-discount-past-one"),
        param("epsilon_start",        1.01, id="a-chance-past-one"),
        param("epsilon_end",          -0.1, id="a-negative-chance"),
        param("exploration_fraction", 0,    id="no-exploration"),
        param("learning_rate",        0,    id="no-learning-rate"),
        param("max_grad_norm",        0,    id="no-gradient-norm"),
        param("sync_steps",           0,    id="no-steps-between-syncs")
    ]
)
def test_the_settings_refuse_a_value_outside_its_range(field: str, value: float):
    """
    Asserts that each setting refuses a value outside the range its field
    declares.
    """
    with raises(ValidationError, match=field):
        AgentSettings(**{field: value})


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


def test_a_batch_values_each_draw_at_the_action_it_took():
    """
    Asserts that a batch reads the value a network gives each draw's action
    on the stack that action was taken on, from a network valuing each of a
    stack's four frames as one action, so action 2 on frames 0 to 3 reads 2
    and action 0 on frames 5 to 8 reads 5.
    """
    batch = Batch(
        actions    = tensor([2, 0]),
        rewards    = tensor([0.0, 0.0]),
        terminated = tensor([False, False]),
        windows    = {Entry.FRAMES: arange(10, dtype=uint8).reshape(2, 5, 1, 1)}
    )

    assert batch.values(
        lambda observations: observations[Entry.FRAMES][:, :, 0, 0].float()
    ).tolist() == [2.0, 5.0]


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


@mark.parametrize(
    ("terminated", "target"),
    [
        param(False, 3.0, id="a-step-the-episode-goes-on-from"),
        param(True,  1.0, id="a-terminated-step")
    ]
)
def test_a_batch_targets_its_reward_plus_the_discounted_highest_value_reached(
    target     : float,
    terminated : bool
):
    """
    Asserts that a batch targets a draw at its reward of one plus 0.5 times
    the highest value a network gives the stack its action reached, which a
    network valuing each of a stack's frames as one action puts at the 4 of
    frames 1 to 4, so 3, and at its reward alone where the step terminated
    the episode, recording no autograd graph either way.
    """
    targets = Batch(
        actions    = tensor([0]),
        rewards    = tensor([1.0]),
        terminated = tensor([terminated]),
        windows    = {Entry.FRAMES: arange(5, dtype=uint8).reshape(1, 5, 1, 1)}
    ).targets(
        0.5,
        lambda observations: (
            observations[Entry.FRAMES][:, :, 0, 0]
            .float()
            .requires_grad_()
        )
    )

    assert (targets.tolist(), targets.requires_grad) == ([target], False)


@mark.parametrize(
    "field",
    [
        param("discount",             id="an-undiscounted-value"),
        param("exploration_fraction", id="exploring-across-the-whole-run")
    ]
)
def test_the_settings_accept_a_fraction_of_one(field: str):
    """
    Asserts that a setting holding a fraction accepts one, the top of the
    range its field declares, where 1.01 is refused.
    """
    assert getattr(AgentSettings(**{field: 1}), field) == 1


def test_a_save_writes_over_the_partial_file_a_killed_save_left(tmp_path: Path):
    """
    Asserts that a save beside the `.partial` file a killed save left behind
    writes over it and leaves the checkpoint alone in its directory.
    """
    (tmp_path / "checkpoint.npz.partial").write_bytes(b"left by a killed save")
    blank().save(tmp_path / "checkpoint.npz")

    assert [path.name for path in tmp_path.iterdir()] == ["checkpoint.npz"]


@mark.parametrize(
    "kept",
    [param(0, id="an-empty-file"), param(0.5, id="its-first-half")]
)
def test_a_checkpoint_cut_short_is_refused_naming_its_file(kept: float, tmp_path: Path):
    """
    Asserts that reading a checkpoint whose file holds nothing or its first
    half alone, as a write the machine lost power during leaves it, raises
    `ValueError` naming the file, the error the commands refuse.
    """
    path = tmp_path / "checkpoint.npz"
    blank(replay={"actions": zeros(64, "int64")}, step=3).save(path)
    truncate(path, int(path.stat().st_size * kept))

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

    monkeypatch.setattr("squirtl.agent.schemas.save_npy", interrupt)

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
    memory holds no array, which `Checkpoint` refuses to read.
    """
    agent = {
        "step"        : 12,
        "online"      : {"weight": tensor([1.0, 2.0])},
        "exploration" : {},
        "optimizer"   : {},
        "sampling"    : {},
        "target"      : {}
    }

    pack(agent, tmp_path / "checkpoint.npz", **{"actions.npy": b"no array"})

    weights = Weights.from_path(tmp_path / "checkpoint.npz")

    assert (weights.online["weight"].tolist(), weights.step) == ([1.0, 2.0], 12)

    with raises(ValueError):
        Checkpoint.from_path(tmp_path / "checkpoint.npz")


@mark.parametrize(
    ("full", "call"),
    [
        param(True,  "fcntl", id="where-fcntl-has-f-fullfsync"),
        param(False, "fsync", id="elsewhere")
    ]
)
def test_a_flush_takes_f_fullfsync_where_fcntl_has_it_and_fsync_elsewhere(
    call        : str,
    full        : bool,
    monkeypatch : MonkeyPatch
):
    """
    Asserts that a flush asks `fcntl` for `F_FULLFSYNC` where the module has
    it, as on macOS, and calls `fsync` where it does not.
    """
    calls = []

    if not full:
        monkeypatch.delattr("fcntl.F_FULLFSYNC", raising=False)

    monkeypatch.setattr(
        "fcntl.fcntl",
        lambda descriptor, command: calls.append("fcntl")
    )
    monkeypatch.setattr(
        "squirtl.agent.schemas.fsync",
        lambda descriptor: calls.append("fsync")
    )
    flush(7)

    assert calls == [call]
