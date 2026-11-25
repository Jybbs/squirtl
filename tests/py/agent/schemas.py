"""
Pins the records the agents read and write, covering:

- The device the settings default to, and the values they refuse, a
  warm-up short of a batch among them
- The values the settings accept at a bound, a fraction of one and a
  warm-up as long as a batch
- The flush that writes a file through the drive's cache
- The agents a run trains, the record of measures each reads, how each
  chooses, the settings each alone reads, and a rollout each refuses as too
  small for its minibatches
- The sums, the averages, and the logged form of an update's measures
"""

from collections.abc import Callable
from common.agents   import each_agent
from pydantic        import ValidationError
from pytest          import MonkeyPatch, mark, param, raises
from torch           import device

from squirtl.agent.schemas import AgentSettings, Algorithm, Measures, PolicyUpdate, Update, flush


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


def test_a_run_trains_the_deep_q_network_unless_it_names_another_agent():
    """
    Asserts that the settings default to the deep Q-network, whose own
    settings sit on the record itself.
    """
    settings = AgentSettings()

    assert (settings.algorithm, settings.hyperparameters) == (Algorithm.DQN, None)


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


def test_a_warmup_as_long_as_the_batch_size_is_accepted():
    """
    Asserts that a warm-up of exactly `batch_size` steps, the shortest the
    settings take, is accepted.
    """
    settings = AgentSettings(batch_size=8, warmup_steps=8)

    assert settings.warmup_steps == settings.batch_size == 8


@mark.parametrize(
    ("algorithm", "read"),
    [
        param(Algorithm.PPO, lambda settings: settings.ppo, id="ppo"),
        param(Algorithm.PQN, lambda settings: settings.pqn, id="pqn")
    ]
)
def test_each_rollout_agent_reads_the_settings_of_its_own(
    algorithm : Algorithm,
    read      : Callable[[AgentSettings], object]
):
    """
    Asserts that `hyperparameters` reads the record of the agent the
    settings name.
    """
    settings = AgentSettings(algorithm=algorithm)

    assert settings.hyperparameters is read(settings)


@each_agent
def test_a_rollout_of_two_samples_per_minibatch_is_the_least_each_agent_accepts(
    algorithm: Algorithm
):
    """
    Asserts that each agent reads its own count of minibatches and its own
    rollout length, three minibatches accepting a rollout of six samples
    and refusing one of five while the other agent's record stands at its
    defaults.
    """
    own = algorithm.value

    assert AgentSettings(
        **{own: {"minibatches": 3, "rollout_steps": 2}},
        algorithm    = algorithm,
        environments = 3
    ).hyperparameters.rollout_steps == 2

    with raises(ValidationError, match="a rollout of 5 samples gives some of its 3"):
        AgentSettings(
            **{own: {"minibatches": 3, "rollout_steps": 1}},
            algorithm    = algorithm,
            environments = 5
        )


def test_measures_log_each_name_beside_its_value_at_four_significant_digits():
    """
    Asserts that a record of measures reads as each name beside its value at
    four significant digits, the form an episode's line logs.
    """
    assert str(Update(loss=2.0, value=-6.54321)) == "loss 2, value -6.543"


@mark.parametrize(
    ("record", "fields"),
    [
        param(Update, {"loss": 1.0, "value": 2.0}, id="the-loss-and-the-value"),
        param(
            PolicyUpdate,
            {
                "clipped"     : 0.25,
                "entropy"     : 1.5,
                "kl"          : 0.01,
                "policy_loss" : -0.5,
                "value_loss"  : 3.0
            },
            id = "ppos-measures"
        )
    ]
)
def test_measures_list_their_totals_and_average_over_a_count(
    fields : dict[str, float],
    record : type[Measures]
):
    """
    Asserts that `totals` lists each measure in the order the record
    declares them, and that `averaged` divides each of them by the count
    back into the record holding the mean of each.
    """
    measures = record(**fields)

    assert measures.totals == tuple(fields.values())
    assert record.averaged(4, [4 * total for total in measures.totals]) == measures


def test_the_deep_q_network_reads_no_minibatches():
    """
    Asserts that a rollout too small for PQN's and PPO's minibatches is
    accepted for the deep Q-network, which collects no rollout.
    """
    short = {"rollout_steps": 1}

    assert AgentSettings(
        environments = 1,
        ppo          = short,
        pqn          = short
    ).algorithm is Algorithm.DQN


@mark.parametrize(
    ("algorithm", "record", "sampled"),
    [
        param(Algorithm.DQN, Update,       False, id="the-deep-q-network"),
        param(Algorithm.PPO, PolicyUpdate, True,  id="ppo"),
        param(Algorithm.PQN, Update,       False, id="pqn")
    ]
)
def test_each_agent_names_its_measures_and_how_it_chooses(
    algorithm : Algorithm,
    record    : type[Measures],
    sampled   : bool
):
    """
    Asserts that each agent reads its own record of measures and samples
    from a policy or chooses epsilon-greedily.
    """
    assert (algorithm.measures, algorithm.sampled) == (record, sampled)
