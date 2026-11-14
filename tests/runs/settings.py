"""
Pins the settings one run reads, covering:

- The default, the bounds, and the description each field of the settings
  declares, the run's own and each subject's, the settings refusing a
  negative seed, and the defaults ending the warm-up inside an anneal
  outlasting a random walk to the starter
- The seed each stream derives from the run's one seed, and the search's
  stream coming after every other
- The curriculum's settings refusing moves whose least passes their most and
  a required share above the completion share, and a run's settings refusing
  a demonstration for the deep Q-network and terms summing past 1 on the way
  to the run's goal
"""

from collections.abc  import Mapping
from json             import dumps
from pathlib          import Path
from pydantic         import ValidationError
from pytest           import mark, param, raises
from syrupy.assertion import SnapshotAssertion

from squirtl.agent.schemas       import AgentSettings, Algorithm
from squirtl.environment.schemas import EnvironmentSettings
from squirtl.reward.schemas      import Event, RewardSettings
from squirtl.runs.settings       import CurriculumSettings, RunSettings, Stream


@mark.parametrize(
    "seed",
    [
        param(1,     id="the-default"),
        param(0,     id="zero"),
        param(2**64, id="past-64-bits")
    ]
)
def test_each_stream_starts_from_a_seed_of_its_own(seed: int):
    """
    Asserts that no two streams of one run start from the same seed,
    whatever non-negative integer the run's seed is, since each stream takes
    a child of its own from the run seed's `SeedSequence`.
    """
    assert len(set(RunSettings(seed=seed).seeds.values())) == len(Stream)


@mark.parametrize(
    ("first", "second"),
    [
        param(1,  2,     id="adjacent"),
        param(0,  2**64, id="apart-by-2-to-the-64")
    ]
)
def test_distinct_run_seeds_share_no_stream_seed(first: int, second: int):
    """
    Asserts that runs taking distinct seeds start no stream from the same
    seed, covering the adjacent pair an offset per stream would collide on
    and the pair a 64-bit mask on the run seed would.
    """
    assert set(RunSettings(seed=first).seeds.values()).isdisjoint(
        RunSettings(seed=second).seeds.values()
    )


def test_each_stream_seed_fits_in_64_unsigned_bits():
    """
    Asserts that every stream's seed is a 64-bit unsigned integer, the
    widest seed `torch.manual_seed` takes.
    """
    assert all(0 <= value < 2**64 for value in RunSettings().seeds.values())


def test_the_default_seed_derives_the_stream_seeds_its_fixture_holds(
    snapshot: SnapshotAssertion
):
    """
    Asserts that the default run seed derives the stream seeds its fixture
    file holds, so a change to the derivation, which would change the draws
    every recorded run's seed reproduces, is reviewed as a diff.
    """
    seeds = RunSettings().seeds

    assert "\n".join(f"{stream} {seed}" for stream, seed in seeds.items()) == snapshot


def test_the_default_warmup_ends_inside_an_anneal_outlasting_a_random_walk():
    """
    Asserts that at the default settings the chance of a random action
    anneals over at least the 37,000 presses a uniform random walk from the
    bedroom can take to reach the starter, and that the warm-up ends before
    that anneal does.
    """
    settings = RunSettings()
    anneal   = settings.agent.exploration_fraction * settings.steps

    assert settings.agent.warmup_steps < anneal and anneal >= 37_000


@mark.parametrize(
    ("goal", "past", "reward"),
    [
        param(
            Event.EVENT_GOT_STARTER,
            "0.21",
            RewardSettings(goal=0.31, milestone=0.3),
            id = "the-starter"
        ),
        param(
            Event.EVENT_GOT_STARTER,
            "2.22e-16",
            RewardSettings(goal=0.343, milestone=0.2, novelty=0.057),
            id = "by-the-rounding-of-a-share"
        ),
        param(
            Event.EVENT_GOT_POKEDEX,
            "0.25",
            RewardSettings(milestone=0.15),
            id = "the-pokedex"
        )
    ]
)
def test_the_settings_refuse_terms_one_step_could_sum_past_one_on_the_way_to_the_goal(
    goal   : Event,
    past   : str,
    reward : RewardSettings
):
    """
    Asserts that the settings refuse terms where a step reaching a new
    position and first setting every flag up to the run's goal at once earns
    past 1, naming the goal and how far past to three significant digits,
    whether the terms sum past 1 in decimal or sum to 1 in decimal and round
    past it once the milestone is counted three times.
    """
    with raises(
        ValidationError,
        match = f"every flag up to {goal.name} at once earns {past} more than the 1"
    ):
        RunSettings(environment=EnvironmentSettings(goal=goal), reward=reward)


@mark.parametrize(
    "reward",
    [
        param(
            RewardSettings(goal=0.5, milestone=0.125, novelty=0.125),
            id = "powers-of-two"
        ),
        param(RewardSettings(goal=0.68, milestone=0.07, novelty=0.11), id="decimals")
    ]
)
def test_the_settings_accept_terms_one_step_sums_to_exactly_one_at_the_goal(
    reward: RewardSettings
):
    """
    Asserts that the settings accept terms where a step reaching a new
    position and first setting every flag up to the starter at once earns
    exactly 1, the most the bound Mnih et al. clip each reward to allows.
    """
    assert RunSettings(reward=reward).reward == reward


@mark.parametrize(
    ("fields", "message"),
    [
        param({"back": (0.8, 0.5)}, r"back\n.*passes the most", id="back"),
        param({"forward": (1.5, 1.0)}, r"forward\n.*passes the most", id="forward"),
        param({"required": 0.96}, "passes the completion share", id="required")
    ]
)
def test_the_curriculums_settings_refuse_bounds_out_of_order(
    fields  : Mapping[str, object],
    message : str
):
    """
    Asserts that the curriculum's settings refuse a least move passing the
    most and a required share passing the completion share.
    """
    with raises(ValidationError, match=message):
        CurriculumSettings.model_validate(fields)


@mark.parametrize(
    "algorithm",
    [param(Algorithm.PPO, id="ppo"), param(Algorithm.PQN, id="pqn")]
)
def test_the_settings_take_a_demonstration_for_pqn_and_ppo(algorithm: Algorithm):
    """
    Asserts that the settings take a demonstration for PQN and PPO.
    """
    RunSettings(
        agent      = AgentSettings(algorithm=algorithm),
        curriculum = CurriculumSettings(demonstration=Path("data/runs/a"))
    )


def test_the_searchs_stream_leaves_the_seed_of_every_earlier_one_as_it_was():
    """
    Asserts that the search's stream comes last among the streams, since
    each stream's seed derives from its place, so every seed an earlier run
    drew from reads as it did.
    """
    assert [*Stream][-1] is Stream.SEARCH


def test_the_settings_carry_the_defaults_and_descriptions_their_fixture_holds(
    snapshot: SnapshotAssertion
):
    """
    Asserts that the run's settings, and each subject's settings they
    hold, carry the default and the bounds each field declares beside the
    description written beneath it, which cyclopts renders as the help of
    that field's flag, so a change to any of them is reviewed as a diff.
    """
    assert dumps(
        RunSettings.model_json_schema(),
        ensure_ascii = False,
        indent       = 2
    ) == snapshot


def test_the_settings_count_no_flag_past_the_goal_toward_the_ceiling():
    """
    Asserts that terms summing past 1 over every flag up to the Pokédex are
    accepted for a run ending at the starter, whose episodes set none of the
    flags after it.
    """
    reward = RewardSettings(milestone=0.15)

    assert RunSettings(reward=reward).reward == reward


def test_the_settings_refuse_a_demonstration_for_the_deep_q_network():
    """
    Asserts that the settings refuse a demonstration beside the deep
    Q-network, which starts every episode in the bedroom.
    """
    with raises(ValidationError, match="takes no demonstration"):
        RunSettings(curriculum=CurriculumSettings(demonstration=Path("data/runs/a")))


def test_the_settings_refuse_a_negative_seed():
    """
    Asserts that a negative seed is refused, since `SeedSequence` takes a
    non-negative integer as its entropy.
    """
    with raises(ValidationError, match="greater than or equal to 0"):
        RunSettings(seed=-1)
