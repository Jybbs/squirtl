"""
Pins the records of a search, covering:

- The defaults of `SearchSettings`, each from the column and the appendix of
  Mhammedi and Cohan's paper its docstring cites, the bound replay memory
  holds them to, and the worker count following the machine
- A range running backward refused
- The order a particle ranks in, and how it reads the starter
- A frontier reading back from JSON as the one written, the generator's
  128-bit state and each kept state's bytes included
"""

from common.search import particle, snapshot
from numpy.random  import default_rng
from os            import process_cpu_count
from pydantic      import ValidationError
from pytest        import MonkeyPatch, mark, param, raises

from squirtl.environment.schemas import EnvironmentSettings
from squirtl.reward.schemas      import Event
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


def test_the_default_capacity_holds_replay_memory_under_a_gigabyte():
    """
    Asserts that the default capacity, each slot one frame at the
    environment's default shape, holds fewer than a billion bytes.
    """
    height, width = EnvironmentSettings().frame_shape

    assert SearchSettings().capacity * height * width < 1_000_000_000


def test_the_settings_default_to_the_papers_montezuma_column():
    """
    Asserts that the population, the rollouts, the chance of a random press,
    and the predictor's settings default to the values the Montezuma's
    Revenge column of Table 5 and Appendices A.2 and A.3 of Mhammedi and
    Cohan's paper give them.
    """
    settings = SearchSettings()

    assert settings.model_dump(exclude={"capacity", "update_steps", "workers"}) == {
        "batch_size"    : 128,
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


@mark.parametrize("field", ["inner_steps", "outer_steps", "rollback"])
def test_a_range_running_backward_is_refused(field: str):
    """
    Asserts that a range whose fewest exceeds its most raises, naming the
    field.
    """
    with raises(ValidationError, match=field):
        SearchSettings(**{field: (3, 2)})


@mark.parametrize("field", ["inner_steps", "outer_steps", "rollback"])
def test_a_range_of_one_value_is_accepted(field: str):
    """
    Asserts that a range whose fewest equals its most is accepted.
    """
    assert getattr(SearchSettings(**{field: (3, 3)}), field) == (3, 3)


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


@mark.parametrize(
    ("events", "terminated"),
    [
        param((), False, id="no-flag"),
        param((Event.EVENT_OAK_APPEARED_IN_PALLET,), False, id="a-milestone"),
        param((Event.EVENT_GOT_STARTER,), True, id="the-starter")
    ]
)
def test_a_particle_terminates_on_the_starters_flag_alone(
    events     : tuple[Event, ...],
    terminated : bool
):
    """
    Asserts that a particle reads as terminated where its snapshot holds
    `EVENT_GOT_STARTER`, and on no other flag.
    """
    assert particle(events=events).terminated is terminated


def test_the_workers_default_to_the_cpus_the_process_may_use(monkeypatch: MonkeyPatch):
    """
    Asserts that the workers default to the count `process_cpu_count`
    reports, or to one where it reports none.
    """
    assert SearchSettings().workers == process_cpu_count()

    monkeypatch.setattr("squirtl.emulator.schemas.process_cpu_count", lambda: None)

    assert SearchSettings().workers == 1
