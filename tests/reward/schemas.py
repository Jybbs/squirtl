"""
Pins the records the reward reads and writes, covering:

- The index each event holds against pret/pokered, the bit each one reads,
  and the term each one earns
- The position read from the symbols holding the map and the coordinates
- The term each of the reward's settings pays, the ceiling they price,
  and the settings they refuse
- The total of a score's shares
"""

from collections.abc import Callable
from operator        import attrgetter
from pydantic        import ValidationError
from pytest          import mark, param, raises

from squirtl.emulator.console import GameBoy
from squirtl.emulator.schemas import Symbol
from squirtl.reward.schemas   import Event, Position, RewardSettings, Score, Term


def test_a_position_reads_the_map_and_coordinates_their_symbols_hold(
    game_boy : GameBoy,
    move     : Callable[[Position], None]
):
    """
    Asserts that a position reads its map from `wCurMap`, its column from
    `wXCoord`, and its row from `wYCoord`, each holding a value of its own.
    """
    position = Position(map=40, x=5, y=3)
    move(position)

    assert Position.read(game_boy) == position


def test_a_score_totals_its_shares():
    """
    Asserts that a score's total is the sum of the share each term earns.
    """
    shares = {Term.MILESTONE: 0.125, Term.NOVELTY: 0.0625, Term.STARTER: 0.5}

    assert Score(shares=shares, terminated=False).total == 0.6875


@mark.parametrize("event", Event, ids=attrgetter("name"))
def test_an_event_reads_as_set_where_its_bit_alone_is_set(
    event    : Event,
    flag     : Callable[[Event], None],
    game_boy : GameBoy
):
    """
    Asserts that setting one event's flag reads that event alone as set.
    """
    flag(event)

    assert Event.read(game_boy) == {event}


@mark.parametrize("event", Event, ids=attrgetter("name"))
def test_an_event_reads_as_clear_where_every_other_bit_is_set(
    event    : Event,
    game_boy : GameBoy
):
    """
    Asserts that an event reads as clear where every bit of memory but its
    own is set, so it reads its own bit and no other.
    """
    byte, bit = divmod(event, 8)
    memory    = game_boy.emulator.memory
    memory[:] = b"\xff" * len(memory)
    memory[Symbol.W_EVENT_FLAGS + byte] ^= 1 << bit

    assert not event.is_set(game_boy)


def test_each_event_earns_the_starter_or_a_milestone():
    """
    Asserts that `EVENT_GOT_STARTER` earns the starter term and every other
    event a milestone.
    """
    assert {event.name: event.term for event in Event} == {
        "EVENT_FOLLOWED_OAK_INTO_LAB"   : Term.MILESTONE,
        "EVENT_GOT_STARTER"             : Term.STARTER,
        "EVENT_OAK_APPEARED_IN_PALLET"  : Term.MILESTONE,
        "EVENT_OAK_ASKED_TO_CHOOSE_MON" : Term.MILESTONE
    }


def test_each_event_holds_the_index_pret_pokered_gives_its_constant():
    """
    Asserts that each event holds the index its constant takes in
    pret/pokered's `constants/event_constants.asm`, counted from the
    `const_def` opening the Pallet Town events.
    """
    assert {event.name: event.value for event in Event} == {
        "EVENT_FOLLOWED_OAK_INTO_LAB"   : 0x00,
        "EVENT_GOT_STARTER"             : 0x22,
        "EVENT_OAK_APPEARED_IN_PALLET"  : 0x27,
        "EVENT_OAK_ASKED_TO_CHOOSE_MON" : 0x21
    }


def test_each_term_reads_the_setting_named_for_it():
    """
    Asserts that each term pays the value of the setting its own value
    names, so no term reads another's setting.
    """
    settings = RewardSettings(milestone=0.125, novelty=0.0625, starter=0.5)

    assert {term: settings.pay(term) for term in Term} == {
        Term.MILESTONE : 0.125,
        Term.NOVELTY   : 0.0625,
        Term.STARTER   : 0.5
    }


@mark.parametrize("field", RewardSettings.model_fields)
@mark.parametrize(
    ("value", "message"),
    [
        param(-0.5, "greater than or equal to 0", id="below-zero"),
        param(1.5,  "less than or equal to 1",    id="above-one")
    ]
)
def test_each_setting_refuses_a_value_outside_zero_to_one(
    field   : str,
    message : str,
    value   : float
):
    """
    Asserts that each setting refuses a value below 0 or above 1, since
    every term pays a step rather than costing it.
    """
    with raises(ValidationError, match=message):
        RewardSettings(**{field: value})


def test_the_settings_accept_a_starter_paying_more_than_every_other_term():
    """
    Asserts that a starter paying half again the milestone is accepted, so
    the starter has only to pay more than every other term.
    """
    assert RewardSettings(milestone=0.125, starter=0.1875).starter == 0.1875


@mark.parametrize(
    "settings",
    [
        param(
            {"milestone": 0.125, "novelty": 0.125, "starter": 0.5},
            id = "powers-of-two"
        ),
        param({"milestone": 0.07, "novelty": 0.11, "starter": 0.68}, id="decimals")
    ]
)
def test_the_settings_accept_terms_one_step_sums_to_one_at_most(
    settings: dict[str, float]
):
    """
    Asserts that the settings accept terms where a step reaching a new
    position and first setting every flag at once earns exactly 1, whether
    each value is a power of two or a decimal whose sum one float addition
    at a time rounds to `1.0000000000000002`.
    """
    assert RewardSettings(**settings).ceiling == 1


@mark.parametrize(
    "settings",
    [
        param({"milestone": 0.125, "starter": 0.125}, id="level-with-a-milestone"),
        param({"novelty": 0.25, "starter": 0.125}, id="below-the-novelty")
    ]
)
def test_the_settings_refuse_a_starter_that_is_not_the_largest_term(
    settings: dict[str, float]
):
    """
    Asserts that a starter paying no more than a milestone or the novelty is
    refused, since the starter has to be the largest term.
    """
    with raises(ValidationError, match="where it has to be the largest term"):
        RewardSettings(**settings)


@mark.parametrize(
    ("settings", "past"),
    [
        param({"milestone": 0.3, "starter": 0.31}, "0.215", id="by-a-share"),
        param(
            {"milestone": 0.2, "novelty": 0.057, "starter": 0.343},
            "2.22e-16",
            id = "by-the-rounding-of-a-share"
        )
    ]
)
def test_the_settings_refuse_terms_one_step_could_sum_past_one(
    past     : str,
    settings : dict[str, float]
):
    """
    Asserts that the settings refuse terms where a step reaching a new
    position and first setting every flag at once earns past 1, naming how
    far past to three significant digits, whether the terms sum past 1 in
    decimal or sum to 1 in decimal and round past it once the milestone is
    counted three times.
    """
    with raises(ValidationError, match=f"earns {past} more than the 1 Mnih et al."):
        RewardSettings(**settings)
