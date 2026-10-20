"""
Pins the wrappers `Overworld.specification` names beside Gymnasium's
own, covering:

- The mean `ShrinkObservation` takes over each square or oblong block of a
  frame small enough to average by hand
- The `Outcome` `RecordOutcome` reports at an episode's last step alone,
  whether `TimeLimit` truncates the episode or the starter ends it
"""

from common.console     import set_event
from gymnasium          import Env
from gymnasium.wrappers import RecordEpisodeStatistics, TimeLimit
from numpy              import array, uint8
from pytest             import fixture, mark, param

from squirtl.environment.overworld import Overworld
from squirtl.environment.schemas   import Outcome
from squirtl.environment.wrappers  import RecordOutcome, ShrinkObservation
from squirtl.reward.schemas        import Event, Term


@fixture
def recorded(overworld: Overworld) -> Env:
    """
    Wraps `overworld` in `RecordOutcome` around `RecordEpisodeStatistics`
    around a `TimeLimit` of three steps, the order `Overworld.specification`
    names them in, and resets it.
    """
    env = RecordOutcome(RecordEpisodeStatistics(TimeLimit(overworld, 3)))
    env.reset(seed=0)

    return env


@mark.parametrize(
    ("frame", "shape", "shrunk"),
    [
        param(
            [[0, 1, 2, 3], [4, 5, 6, 8], [255, 255, 9, 9], [255, 254, 9, 10]],
            (2, 2),
            [[3, 5], [255, 9]],
            id = "blocks-of-2-by-2"
        ),
        param(
            [[0, 1, 2, 3, 4, 5], [6, 7, 8, 9, 10, 14]],
            (1, 2),
            [[4, 8]],
            id = "blocks-of-2-by-3"
        )
    ]
)
def test_a_frame_shrinks_to_the_mean_of_each_block_rounding_a_half_up(
    frame     : list[list[int]],
    overworld : Overworld,
    shape     : tuple[int, int],
    shrunk    : list[list[int]]
):
    """
    Asserts that a frame shrinks into `shape` cells of `uint8`, each its
    block's mean with a half rounded up, so 2.5 becomes 3, 7.5 becomes 8,
    and 9.25 becomes 9, with no sum overflowing near 255 and no block taking
    in its neighbors' pixels.
    """
    result = ShrinkObservation(overworld, shape).observation(array(frame, uint8))

    assert (result.tolist(), result.dtype) == (shrunk, uint8)


@mark.usefixtures("walking")
def test_a_truncated_episode_reports_its_outcome_at_its_last_step_alone(recorded: Env):
    """
    Asserts that an episode `TimeLimit` truncates after three steps, each
    reaching a new square at 0.0625, reports no outcome before its last step
    and there the three steps, the four positions its start included, the
    return of 0.1875 the novelty pays, the time `RecordEpisodeStatistics`
    records, and no termination.
    """
    infos = [recorded.step(0)[4] for _ in range(3)]

    assert ["outcome" in info for info in infos] == [False, False, True]
    assert infos[-1]["outcome"] == Outcome(
        length     = 3,
        positions  = 4,
        reward     = 0.1875,
        seconds    = infos[-1]["episode"]["t"],
        shares     = {Term.MILESTONE: 0.0, Term.NOVELTY: 0.1875, Term.STARTER: 0.0},
        terminated = False
    )


def test_an_episode_reaching_the_starter_reports_its_termination(
    overworld : Overworld,
    recorded  : Env
):
    """
    Asserts that an episode whose first step sets the starter's flag reports
    there an outcome of one step that terminated, paying the starter alone.
    """
    set_event(Event.EVENT_GOT_STARTER, overworld.game_boy.emulator.memory)
    *_, terminated, truncated, info = recorded.step(0)

    assert (terminated, truncated, info["outcome"].length, info["outcome"].shares) == (
        True, False, 1,
        {Term.MILESTONE: 0.0, Term.NOVELTY: 0.0, Term.STARTER: 0.5}
    )
