"""
Pins replay memory, covering:

- Each transition it holds drawn back as it was stored, every entry as deep
  as its space declares, and each one it releases once overwritten
- A reset observation drawn back element by element, and a `Box` bounded
  at 0 and 1 held unpacked in its own dtype
- The generator its draws come from, and the memory its default capacity
  takes with each `MultiBinary` entry packed eight cells to a byte
"""

from collections.abc  import Callable, Mapping
from gymnasium.spaces import Box, Dict, MultiBinary
from itertools        import pairwise
from numpy            import arange, array, float32, ndarray, uint8, zeros
from numpy.random     import default_rng
from pytest           import fixture, mark, param
from torch.testing    import assert_close

from squirtl.agent.replay        import Replay
from squirtl.agent.schemas       import AgentSettings
from squirtl.environment.schemas import Entry

type Stacked = Callable[[Mapping[str, ndarray], Dict], list[dict[str, ndarray]]]


@fixture
def tiny() -> Dict:
    """
    Declares an observation of four stacked one-pixel frames beside a vector
    of two flags and a binary 3 by 10 grid, each one deep and each element
    small enough to name the step it was stored on, the grid's rows 10 cells
    wide so packing them leaves a byte part full.
    """
    return Dict(
        {
            Entry.FLAGS  : Box(0, 255, (1, 2), uint8),
            Entry.FRAMES : Box(0, 255, (4, 1, 1), uint8),
            Entry.GRID   : MultiBinary((1, 3, 10))
        }
    )


def elements(index: int, steps: int) -> dict[str, ndarray]:
    """
    Builds the elements of episode `index`, `steps` steps long, each step's
    frame holding its step plus 100 times `index`, its flags that value
    and that value plus 50, and its grid that value's eight bits, repeated
    across the grid's cells.
    """
    values = arange(steps + 1, dtype=uint8) + 100 * index

    return {
        Entry.FLAGS  : values[:, None] + array([0, 50], uint8),
        Entry.FRAMES : values[:, None, None],
        Entry.GRID   : values[:, None, None] >> arange(30, dtype=uint8).reshape(
            3,
            10
        ) % 8 & 1
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
    transitions stored, each with both observations, its action, its reward,
    and its termination, and never one reaching across two episodes or into
    an element written since, each episode terminated or truncated by its
    row.
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


def test_replay_at_its_default_capacity_packs_each_binary_entry_into_606_mb(
    space: Dict
):
    """
    Asserts that replay memory at the default capacity takes 606.3 MB for
    the environment's observation, a slot holding a 72 by 80 frame, the grid
    packed into 288 bytes, the flags into one, and 14 bytes for its action,
    reward, termination, and whether it holds a transition.
    """
    replay = Replay(AgentSettings().capacity, default_rng(0), space)

    assert sum(
        allocated.nbytes
        for allocated in [
            *vars(replay).values(),
            *(column.elements for column in replay.columns.values())
        ]
        if isinstance(allocated, ndarray)
    ) == 606_300_000


def test_replay_draws_a_reset_observation_back_element_by_element(tiny: Dict):
    """
    Asserts that replay memory draws back a reset observation whose frames
    differ from one another as the observation the first action was taken
    on, each frame in the slot it was stored in.
    """
    replay = Replay(16, default_rng(0), tiny)
    frames = arange(1, 6, dtype=uint8).reshape(5, 1, 1)

    grid = zeros((1, 3, 10), uint8)

    replay.begin(
        {
            Entry.FLAGS  : array([[1, 2]], uint8),
            Entry.FRAMES : frames[:4],
            Entry.GRID   : grid
        }
    )
    replay.store(
        0,
        {
            Entry.FLAGS  : array([[3, 4]], uint8),
            Entry.FRAMES : frames[1:],
            Entry.GRID   : grid
        },
        0.0,
        False
    )

    assert replay.sample("cpu", 1).observations[Entry.FRAMES].flatten().tolist() == [
        1, 2, 3, 4
    ]


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

    assert_close(first.model_dump(), second.model_dump(), atol=0, rtol=0)


def test_replay_holds_a_box_bounded_at_0_and_1_unpacked_in_its_dtype():
    """
    Asserts that replay memory stores a `Box` entry bounded at 0 and 1 as it
    is rather than packed, drawing it back in its own dtype.
    """
    replay = Replay(8, default_rng(0), Dict({Entry.FLAGS: Box(0, 1, (1, 2), float32)}))

    replay.begin({Entry.FLAGS: array([[0, 1]], float32)})
    replay.store(0, {Entry.FLAGS: array([[1, 0]], float32)}, 0.0, False)

    assert replay.sample("cpu", 1).windows[Entry.FLAGS].tolist() == [
        [[0.0, 1.0], [1.0, 0.0]]
    ]
