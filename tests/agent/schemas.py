"""
Pins the records the agent reads and writes, covering:

- The device the settings default to, the values each setting refuses,
  and the bound a fraction accepts
- The value a batch reads for each draw's action and the target it sets
  each draw
- A checkpoint reading back as the one written, and refusing a file that
  holds anything beyond tensors and plain values
"""

from pathlib  import Path
from pickle   import UnpicklingError
from pydantic import ValidationError
from pytest   import MonkeyPatch, mark, param, raises
from torch    import arange, device, equal, save, tensor, uint8

from squirtl.agent.schemas import AgentSettings, Batch, Checkpoint


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
        window     = arange(10, dtype=uint8).reshape(2, 5, 1, 1)
    )

    assert batch.values(lambda stacks: stacks[:, :, 0, 0].float()).tolist() == [
        2.0, 5.0
    ]


def test_a_checkpoint_reads_back_as_the_one_written(tmp_path: Path):
    """
    Asserts that a checkpoint written to a file reads back with every field
    equal to the one written.
    """
    written = Checkpoint(
        exploration = {"bit_generator": "PCG64", "state": {"inc": 1, "state": 2**100}},
        online      = {"weight": tensor([1.0, 2.0])},
        optimizer   = {"param_groups": [{"lr": 1e-4, "params": [0]}], "state": {}},
        sampling    = {"bit_generator": "PCG64", "state": {"inc": 5, "state": 3}},
        step        = 12,
        target      = {"weight": tensor([0.5, 2.0])}
    )
    written.save(tmp_path / "checkpoint.pt")
    read = Checkpoint.from_path(tmp_path / "checkpoint.pt")

    assert equal(read.online["weight"], written.online["weight"])
    assert equal(read.target["weight"], written.target["weight"])
    assert (read.exploration, read.optimizer, read.sampling, read.step) == (
        written.exploration, written.optimizer, written.sampling, written.step
    )


def test_a_checkpoint_refuses_a_file_holding_an_arbitrary_object(tmp_path: Path):
    """
    Asserts that reading a checkpoint refuses a file whose pickle holds an
    object beyond tensors and plain values, which `torch.load`'s default
    `weights_only=True` unpickles alone.
    """
    save({"online": Path("online.pt")}, tmp_path / "checkpoint.pt")

    with raises(UnpicklingError, match="Weights only load failed"):
        Checkpoint.from_path(tmp_path / "checkpoint.pt")


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
        window     = arange(5, dtype=uint8).reshape(1, 5, 1, 1)
    ).targets(0.5, lambda stacks: stacks[:, :, 0, 0].float().requires_grad_())

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
