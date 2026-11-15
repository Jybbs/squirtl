"""
Pins the records of a search, covering:

- The order a particle ranks in
- A frontier reading back from JSON as the one written, the generator's
  128-bit state and each kept state's bytes included
- The defaults of `SearchSettings`, each from the column and the appendix of
  Mhammedi and Cohan's paper its docstring cites, the bound replay memory
  holds them to, the worker count following the machine, a range running
  backward refused, and a range of one value accepted
"""

from common.search import particle, snapshot
from numpy.random  import default_rng
from pydantic      import ValidationError
from pytest        import MonkeyPatch, mark, param, raises

from squirtl.environment.schemas import EnvironmentSettings
from squirtl.search.schemas      import Frontier, SearchSettings


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


def test_a_range_of_one_value_is_accepted(ranged: str):
    """
    Asserts that a range whose fewest equals its most is accepted.
    """
    assert getattr(SearchSettings(**{ranged: (3, 3)}), ranged) == (3, 3)


def test_a_range_running_backward_is_refused(ranged: str):
    """
    Asserts that a range whose fewest exceeds its most raises, naming the
    field.
    """
    with raises(ValidationError, match=rf"{ranged}\n.*passes the most"):
        SearchSettings(**{ranged: (3, 2)})


def test_the_default_capacity_holds_replay_memory_under_three_gigabytes():
    """
    Asserts that the default capacity, each slot one frame at the
    environment's default shape, holds fewer than three billion bytes.
    """
    height, width = EnvironmentSettings().frame_shape

    assert SearchSettings().capacity * height * width < 3_000_000_000


def test_the_settings_default_to_the_papers_montezuma_column():
    """
    Asserts that the population, the rollouts, the chance of a random press,
    and the predictor's settings and replay memory default to the values
    the Montezuma's Revenge column of Table 5 and Appendices A.2 and A.3 of
    Mhammedi and Cohan's paper give them.
    """
    assert SearchSettings().model_dump(exclude={"update_steps", "workers"}) == {
        "batch_size"    : 128,
        "capacity"      : 512_000,
        "epsilon"       : 0.2,
        "groups"        : 4,
        "learning_rate" : 3e-4,
        "particles"     : 32,
        "inner_steps"   : (5, 15),
        "outer_steps"   : (10, 20),
        "rollback"      : (1, 3)
    }


def test_the_updates_default_to_the_ratio_of_the_papers_table():
    """
    Asserts that the presses between updates of the predictor default to the
    400 million frames of Mhammedi and Cohan's Table 6, four frames a press,
    over its 2.28 million updates, rounded.
    """
    assert SearchSettings().update_steps == round(400_000_000 / 4 / 2_280_000)


@mark.parametrize(
    ("reported", "workers"),
    [param(4, 4, id="the-cpus-reported"), param(None, 1, id="one-where-none-is")]
)
def test_the_workers_default_to_the_cpus_the_process_may_use(
    monkeypatch : MonkeyPatch,
    reported    : int | None,
    workers     : int
):
    """
    Asserts that the workers default to the count `process_cpu_count`
    reports, or to one where it reports none.
    """
    monkeypatch.setattr("squirtl.emulator.schemas.process_cpu_count", lambda: reported)

    assert SearchSettings().workers == workers
