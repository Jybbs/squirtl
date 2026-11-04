"""
Pins the records the agent reads and writes, covering:

- The device the settings default to, and the values they refuse, a
  warm-up short of a batch among them
- The values the settings accept at a bound, a fraction of one and a
  warm-up as long as a batch
- The flush that writes a file through the drive's cache
"""

from pydantic import ValidationError
from pytest   import MonkeyPatch, mark, param, raises
from torch    import device

from squirtl.agent.schemas import AgentSettings, flush


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
        "torch.accelerator.current_accelerator",
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
        param("sync_steps",           0,    id="no-steps-between-syncs"),
        param("threads",              0,    id="no-threads"),
        param("update_steps",         0,    id="no-steps-between-updates"),
        param("warmup_steps",         0,    id="no-warmup")
    ]
)
def test_the_settings_refuse_a_value_outside_its_range(field: str, value: float):
    """
    Asserts that each setting refuses a value outside the range its field
    declares, the error located at that field.
    """
    with raises(ValidationError, match=rf"(?m)^{field}$"):
        AgentSettings(**{field: value})


@mark.parametrize(
    ("batch_size", "warmup_steps", "message"),
    [
        param(
            32,
            31,
            "a warm-up of 31 steps gathers fewer transitions than the 32 each update "
            "draws",
            id = "a-step-short-of-the-default-batch"
        ),
        param(
            2048,
            1000,
            "a warm-up of 1,000 steps gathers fewer transitions than the 2,048 each "
            "update draws",
            id = "a-batch-past-a-thousand"
        )
    ]
)
def test_a_warmup_short_of_the_batch_size_is_refused(
    batch_size   : int,
    message      : str,
    warmup_steps : int
):
    """
    Asserts that a warm-up of fewer steps than `batch_size` is refused, the
    error naming the warm-up and the batch each update draws, each with its
    thousands separated.
    """
    with raises(ValidationError, match=message):
        AgentSettings(batch_size=batch_size, warmup_steps=warmup_steps)


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


def test_a_warmup_as_long_as_the_batch_size_is_accepted():
    """
    Asserts that a warm-up of exactly `batch_size` steps, the shortest the
    settings take, is accepted.
    """
    settings = AgentSettings(batch_size=8, warmup_steps=8)

    assert settings.warmup_steps == settings.batch_size == 8


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
    it, as on macOS, and calls `fsync` where it does not, as on Linux, each
    platform's module stood in for on the other.
    """
    calls = []

    if full:
        monkeypatch.setattr("fcntl.F_FULLFSYNC", 51, raising=False)
    else:
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
