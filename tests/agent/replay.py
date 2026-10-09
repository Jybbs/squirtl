"""
Pins replay memory, covering:

- The transitions it holds, each drawn back as the stacks, action, reward,
  and termination it was stored from
- The transitions it releases once their frames are overwritten
- The draws coming from the generator it is built with
- The memory its default capacity takes at four stacked 72 by 80 frames
"""

from collections.abc import Callable
from itertools       import pairwise
from numpy           import arange, ndarray, uint8
from numpy.random    import default_rng
from pytest          import mark, param
from torch           import equal

from squirtl.agent.replay  import Replay
from squirtl.agent.schemas import AgentSettings


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
    episode  : Callable[[ndarray], list[ndarray]]
):
    """
    Asserts that replay memory draws back exactly the last `held`
    transitions stored, each as the stacks its action was taken on and
    reached, its action, its reward, and whether it terminated the episode,
    and never a stack reaching across two episodes or into a frame written
    since.

    Each episode ends on its last step, terminated where its row says so
    and otherwise truncated, as a time limit ends one, whose last transition
    keeps the observation it reached.
    """
    replay = Replay(capacity, default_rng(0), (4, 1, 1))
    stored = []

    for index, (steps, terminated) in enumerate(episodes):
        observations = episode(
            arange(steps + 1, dtype=uint8)[:, None, None] + 100 * index
        )
        replay.begin(observations[0])

        for step, (observation, reached) in enumerate(pairwise(observations)):
            last = terminated and step == steps - 1
            replay.store(step % 7, reached, step, last)
            stored.append(
                (observation.tobytes(), step % 7, step, last, reached.tobytes())
            )

    batch = replay.sample("cpu", 500)

    assert len(replay) == held
    assert {
        (
            observation.numpy().tobytes(),
            action, reward, terminated,
            reached.numpy().tobytes()
        )
        for observation, action, reward, terminated, reached in zip(
            batch.observations,
            batch.actions.tolist(),
            batch.rewards.tolist(),
            batch.terminated.tolist(),
            batch.next_observations,
            strict = True
        )
    } == set(stored[-held:])


def test_replay_at_its_default_capacity_holds_its_arrays_under_a_gigabyte():
    """
    Asserts that the arrays of replay memory at the default capacity take
    less than 1 GB for four stacked 72 by 80 frames, each slot holding one
    `uint8` frame.
    """
    replay = Replay(AgentSettings().capacity, default_rng(0), (4, 72, 80))

    assert sum(
        array.nbytes for array in vars(replay).values() if isinstance(array, ndarray)
    ) < 10**9


def test_replay_draws_each_batch_from_the_generator_it_is_built_with(
    episode: Callable[[ndarray], list[ndarray]]
):
    """
    Asserts that two replay memories holding the same transitions and built
    with generators from the same seed draw the same batch.
    """
    observations = episode(arange(21, dtype=uint8)[:, None, None])
    replays      = [Replay(64, default_rng(3), (4, 1, 1)) for _ in range(2)]

    for replay in replays:
        replay.begin(observations[0])

        for step, reached in enumerate(observations[1:]):
            replay.store(step % 7, reached, 0.0, False)

    first, second = (replay.sample("cpu", 32) for replay in replays)

    assert all(map(equal, vars(first).values(), vars(second).values()))
