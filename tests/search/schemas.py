"""
Pins the records of a search, covering:

- The order a particle ranks in
- A frontier reading back from JSON as the one written, the generator's
  128-bit state and each kept state's bytes included
"""

from common.search import particle, snapshot
from numpy.random  import default_rng
from pytest        import mark, param

from squirtl.search.schemas import Frontier


def test_a_frontier_reads_back_from_json_as_the_one_written():
    """
    Asserts that a frontier reads back from its JSON equal to the one
    written, with the 128-bit integers of the generator's state exact and
    the kept states under their integer nodes.
    """
    frontier = Frontier(
        groups     = [particle(reward=0.1, score=0.3)],
        iterations = 2,
        planning   = default_rng(7).bit_generator.state,
        presses    = 12,
        states     = {0: snapshot(shade=9), 4: snapshot(shade=3)},
        winner     = particle(reward=0.1, score=0.3)
    )

    assert Frontier.model_validate_json(frontier.model_dump_json()) == frontier


@mark.parametrize(
    ("better", "worse"),
    [
        param({"reward": 0.1}, {"reward": 0.0, "score": 9.0}, id="reward-over-score"),
        param({"score": 0.2},  {"score": 0.1},                id="score-breaks-a-tie")
    ]
)
def test_a_particle_ranks_by_its_reward_and_then_its_uncertainty(
    better : dict[str, float],
    worse  : dict[str, float]
):
    """
    Asserts that more reward outranks any uncertainty, and that the higher
    uncertainty ranks first among equal rewards.
    """
    assert particle(**better).rank > particle(**worse).rank
