"""
Pins `Rollout`, covering:

- Each step's λ-return on a rollout worked by hand, cut at an episode's
  termination, bootstrapped from the final observation at a truncation, a
  one-step target at a λ of 0, and a discounted sum at a λ of 1
- The λ-return less each step's value, which is Schulman et al.'s
  generalized advantage estimate
- The columns of two environments, which end their episodes apart
- What each step stores, and the tensors an update reads along one axis on
  the device it names
"""

from gymnasium.spaces import Dict
from numpy            import array, float32, ones, zeros
from numpy.testing    import assert_allclose, assert_array_equal
from pytest           import fixture, mark, param
from torch            import equal, tensor

from squirtl.agent.rollout       import Rollout
from squirtl.environment.schemas import Entry


@fixture
def rollout(space: Dict) -> Rollout:
    """
    Builds a rollout of three steps in one environment, each earning a
    reward of 1, whose steps are valued at 0.5, 1.0, and 2.0.
    """
    built              = Rollout(1, space, 3)
    built.rewards[:]   = 1
    built.values[:, 0] = [0.5, 1.0, 2.0]

    return built


@mark.parametrize(
    ("decay", "end", "row", "returns"),
    [
        param(0.5, None,         0, [1.8125, 2.25, 3.0],   id="no-episode-ending"),
        param(0.5, "terminated", 1, [1.5, 1.0, 3.0],       id="a-termination-midway"),
        param(0.5, "terminated", 2, [1.6875, 1.75, 1.0],   id="a-termination-last"),
        param(0.5, "truncated",  1, [2.5, 5.0, 3.0],       id="a-truncation-midway"),
        param(0.5, "truncated",  2, [1.9375, 2.75, 5.0],   id="a-truncation-last"),
        param(0.0, None,         0, [1.5, 2.0, 3.0],       id="a-decay-of-zero"),
        param(1.0, None,         0, [2.25, 2.5, 3.0],      id="a-decay-of-one")
    ]
)
def test_each_step_mixes_the_value_it_reached_with_the_return_after_it(
    decay   : float,
    end     : str | None,
    returns : list[float],
    rollout : Rollout,
    row     : int
):
    """
    Asserts that at a discount of 0.5 and a last value of 4, each λ-return
    is the reward of 1 plus half of the value the step reached mixed with
    the next λ-return at a weight of `decay`, the rows worked by hand. The
    mix cuts at a termination, which adds no value, and at a truncation,
    which adds the 8.0 its final observation is valued at.
    """
    if end:
        getattr(rollout, end)[row, 0] = True
        rollout.bootstraps[row, 0]    = 8.0 if end == "truncated" else 0.0

    assert_allclose(rollout.returns(decay, 0.5, array([4.0], float32))[:, 0], returns)


def test_a_batch_lays_every_step_along_one_axis(space: Dict):
    """
    Asserts that `batch` lays out each array an update reads along one
    axis, keeping the rest of its shape, the entries of the observations and
    `returns` among them.
    """
    rollout            = Rollout(2, space, 3)
    rollout.actions[:] = [[0, 1], [2, 3], [4, 5]]
    batch              = rollout.batch("cpu", zeros((3, 2), float32))

    assert equal(batch["actions"], tensor([0, 1, 2, 3, 4, 5]))
    assert batch["returns"].shape == (6,)
    assert batch["frames"].shape == (6, *space["frames"].shape)
    assert batch.keys() == {*space, "actions", "log_probs", "returns", "values"}


def test_a_batch_moves_each_array_onto_the_device_it_names(space: Dict):
    """
    Asserts that `batch` moves every array an update reads onto the device
    it names, which the `meta` device pins on a machine with no accelerator.
    """
    batch = Rollout(2, space, 3).batch("meta", zeros((3, 2), float32))

    assert {array.device.type for array in batch.values()} == {"meta"}


def test_a_step_stores_its_outcome_in_its_row_alone(space: Dict):
    """
    Asserts that storing an outcome writes its row's rewards, ends, and
    bootstraps, leaving every other row at zero.
    """
    rollout     = Rollout(2, space, 2)
    rollout.row = 1
    rollout.store_outcome(
        bootstraps = array([0.0, 7.0], float32),
        rewards    = array([1.0, 2.0], float32),
        terminated = array([True, False]),
        truncated  = array([False, True])
    )

    assert_array_equal(rollout.bootstraps, [[0, 0], [0, 7]])
    assert_array_equal(rollout.rewards, [[0, 0], [1, 2]])
    assert_array_equal(rollout.terminated, [[False, False], [True, False]])
    assert_array_equal(rollout.truncated, [[False, False], [False, True]])
    assert rollout.row == 2


@mark.parametrize(
    ("log_probs", "stored"),
    [
        param(None,                     [0.0, 0.0],   id="no-log-probabilities"),
        param(array([-0.5, -2.5], float32), [-0.5, -2.5], id="each-log-probability")
    ]
)
def test_a_step_stores_what_it_acted_on_in_its_row_alone(
    log_probs : object,
    space     : Dict,
    stored    : list[float]
):
    """
    Asserts that storing an action writes its row's observations, actions,
    and values, and each action's log-probability where the agent reads one,
    leaving every other row at zero.
    """
    rollout     = Rollout(2, space, 3)
    rollout.row = 1
    rollout.store_action(
        actions      = array([3, 5]),
        log_probs    = log_probs,
        observations = {
            key: ones((2, *entry.shape), entry.dtype) for key, entry in space.items()
        },
        values = array([0.25, 0.75], float32)
    )

    assert_array_equal(rollout.actions, [[0, 0], [3, 5], [0, 0]])
    assert_array_equal(rollout.values, [[0, 0], [0.25, 0.75], [0, 0]])
    assert_array_equal(rollout.log_probs, [[0, 0], stored, [0, 0]])
    assert rollout.observations[Entry.FRAMES][1].all()
    assert not rollout.observations[Entry.FRAMES][[0, 2]].any()


def test_each_column_ends_its_own_episodes(space: Dict):
    """
    Asserts that one environment's termination cuts only its own column, the
    two columns holding the λ-returns each would hold alone.
    """
    rollout              = Rollout(2, space, 3)
    rollout.rewards[:]   = 1
    rollout.values[:, :] = array([[0.5], [1.0], [2.0]], float32)
    rollout.terminated[1, 1] = True

    assert_allclose(
        rollout.returns(0.5, 0.5, array([4.0, 4.0], float32)),
        [[1.8125, 1.5], [2.25, 1.0], [3.0, 3.0]]
    )


def test_the_return_less_the_value_is_the_generalized_advantage_estimate(
    rollout: Rollout
):
    """
    Asserts that each λ-return less its step's value equals Schulman et
    al.'s estimate, each temporal-difference error plus the discounted,
    decayed estimate after it, which at a discount and a decay of 0.5 gives
    1.3125, 1.25, and 1 from three errors of 1.
    """
    assert_allclose(
        rollout.returns(0.5, 0.5, array([4.0], float32))[:, 0] - rollout.values[:, 0],
        [1.3125, 1.25, 1.0]
    )
