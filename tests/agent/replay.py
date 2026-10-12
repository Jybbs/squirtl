"""
Pins replay memory, covering:

- The transitions it holds, each drawn back as the observations, action,
  reward, and termination it was stored from, every entry stacked as deep
  as its space declares
- The transitions it releases once their elements are overwritten
- The draws coming from the generator it is built with
- The memory its default capacity takes at the observation the
  environment makes
"""

from collections.abc  import Callable, Mapping
from gymnasium.spaces import Box, Dict
from itertools        import pairwise
from numpy            import arange, array, ndarray, uint8
from numpy.random     import default_rng
from pytest           import fixture, mark, param
from torch.testing    import assert_close

from squirtl.agent.replay  import Replay
from squirtl.agent.schemas import AgentSettings

type Stacked = Callable[[Mapping[str, ndarray], Dict], list[dict[str, ndarray]]]


@fixture
def tiny() -> Dict:
    """
    Declares an observation of four stacked one-pixel frames beside a vector
    of two flags one deep, each element small enough to name the step it was
    stored on.
    """
    return Dict(flags=Box(0, 255, (1, 2), uint8), frames=Box(0, 255, (4, 1, 1), uint8))


def elements(index: int, steps: int) -> dict[str, ndarray]:
    """
    Builds the elements of episode `index`, `steps` steps long, each step's
    frame holding its step plus 100 times `index` and its flags that value
    and that value plus 50.
    """
    values = arange(steps + 1, dtype=uint8) + 100 * index

    return {
        "flags"  : values[:, None] + array([0, 50], uint8),
        "frames" : values[:, None, None]
    }


@mark.parametrize(
    ("capacity", "episodes", "held"),
    [
        param(64, [(5, True), (3, False)], 8, id="two-episodes-within-capacity"),
        param(12, [(5, True), (6, False)], 6, id="an-episode-overwritten"),
        param(10, [(20, False)],           6, id="one-episode-past-capacity")
    ]
)
def test_replay_draws_back_each_transition_it_holds_and_nothing_else(
    capacity : int,
    episodes : list[tuple[int, bool]],
    held     : int,
    stacked  : Stacked,
    tiny     : Dict
):
    """
    Asserts that replay memory draws back exactly the last `held`
    transitions stored, each as the observation its action was taken on and
    the one it reached, its action, its reward, and whether it terminated
    the episode, and never an observation reaching across two episodes or
    into an element written since.

    Each episode ends on its last step, terminated where its row says so
    and otherwise truncated, as a time limit ends one, whose last transition
    keeps the observation it reached.
    """
    replay = Replay(capacity, default_rng(0), tiny)
    stored = []

    for index, (steps, terminated) in enumerate(episodes):
        observations = stacked(elements(index, steps), tiny)
        replay.begin(observations[0])

        for step, (observation, reached) in enumerate(pairwise(observations)):
            last = terminated and step == steps - 1
            replay.store(step % 7, reached, step, last)
            stored.append(
                (
                    *(observation[key].tobytes() for key in tiny),
                    step % 7,
                    step, last,
                    *(reached[key].tobytes() for key in tiny)
                )
            )

    batch = replay.sample("cpu", 500)

    assert len(replay) == held
    assert {
        (
            *(batch.observations[key][draw].numpy().tobytes() for key in tiny),
            action, reward, terminated,
            *(batch.next_observations[key][draw].numpy().tobytes() for key in tiny)
        )
        for draw, (action, reward, terminated) in enumerate(
            zip(
                batch.actions.tolist(),
                batch.rewards.tolist(),
                batch.terminated.tolist(),
                strict = True
            )
        )
    } == set(stored[-held:])


def test_replay_at_its_default_capacity_holds_its_arrays_under_a_gigabyte(space: Dict):
    """
    Asserts that the arrays of replay memory at the default capacity take
    less than 1 GB for the observation the environment makes, each slot
    holding one `uint8` 72 by 80 frame, one 48 by 48 grid, and four flags.
    """
    replay = Replay(AgentSettings().capacity, default_rng(0), space)

    assert sum(
        allocated.nbytes
        for allocated in [*vars(replay).values(), *replay.observations.values()]
        if isinstance(allocated, ndarray)
    ) < 10**9


def test_replay_draws_each_batch_from_the_generator_it_is_built_with(
    stacked : Stacked,
    tiny    : Dict
):
    """
    Asserts that two replay memories holding the same transitions and built
    with generators from the same seed draw the same batch.
    """
    observations = stacked(elements(0, 20), tiny)
    replays      = [Replay(64, default_rng(3), tiny) for _ in range(2)]

    for replay in replays:
        replay.begin(observations[0])

        for step, reached in enumerate(observations[1:]):
            replay.store(step % 7, reached, 0.0, False)

    first, second = (replay.sample("cpu", 32) for replay in replays)

    assert_close(vars(first), vars(second), atol=0, rtol=0)
