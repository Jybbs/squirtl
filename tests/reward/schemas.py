"""
Pins the records the reward reads and writes, covering:

- The index each event holds against pret/pokered, the order the opening
  sets them in, the bit each one reads, the term each one earns toward each
  goal, and the names it is read and written by
- The position read from the symbols holding the map and the coordinates
- The term each of the reward's settings pays, the ceiling they price for
  each goal, the reward for the flags a count of terms holds, and the
  settings they refuse
- The total of a score's shares
"""

from collections.abc import Callable
from itertools       import takewhile
from operator        import attrgetter
from pydantic        import TypeAdapter, ValidationError
from pytest          import approx, mark, param, raises

from squirtl.emulator.console import GameBoy
from squirtl.emulator.schemas import Symbol
from squirtl.reward.schemas   import Event, Flag, Position, RewardSettings, Score, Term


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
    shares = {Term.GOAL: 0.5, Term.MILESTONE: 0.125, Term.NOVELTY: 0.0625}

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


@mark.parametrize("goal", Event, ids=attrgetter("name"))
def test_each_event_before_a_goal_earns_a_milestone_and_the_goal_its_own_term(
    goal: Event
):
    """
    Asserts that an episode ending at `goal` pays a milestone for each event
    `Event` declares before it and the goal term for the goal itself, in the
    order `Event` declares them, and nothing for any event after it.
    """
    assert list(goal.terms.items()) == [
        *((event, Term.MILESTONE) for event in takewhile(
            lambda event: event is not goal,
            Event
        )),
        (goal, Term.GOAL)
    ]


def test_an_event_refuses_a_name_no_member_holds():
    """
    Asserts that a name no member of `Event` holds is refused, as an index
    no member holds is.
    """
    with raises(ValueError, match="is not a valid Event"):
        Event("EVENT_GOT_BICYCLE")


@mark.parametrize(
    "name",
    [
        param("EVENT_GOT_POKEDEX", id="as-event-declares-it"),
        param("event-got-pokedex", id="as-cyclopts-lists-it")
    ]
)
def test_an_event_is_read_by_its_name_and_written_to_json_by_it(name: str):
    """
    Asserts that an event reads from its name, spelled as `Event` declares
    it or as cyclopts lists it among a flag's choices, through `Event` and
    through `Flag` alike, and that `Flag` writes it to JSON by the name
    `Event` declares.
    """
    adapter = TypeAdapter(Flag)

    assert [
        Event(name),
        adapter.validate_python(name),
        adapter.dump_json(Event.EVENT_GOT_POKEDEX)
    ] == [Event.EVENT_GOT_POKEDEX, Event.EVENT_GOT_POKEDEX, b'"EVENT_GOT_POKEDEX"']


def test_each_event_holds_its_index_in_pret_pokered_in_the_order_the_opening_sets_them(
):
    """
    Asserts that each event holds the index its constant takes in
    pret/pokered's `constants/event_constants.asm`, counted from the
    `const_def` opening the Pallet Town events, and that `Event` declares
    them in the order the opening sets them, from Oak appearing in Pallet
    Town to the Pokédex.
    """
    assert [(event.name, event.value) for event in Event] == [
        ("EVENT_OAK_APPEARED_IN_PALLET", 0x27),
        ("EVENT_FOLLOWED_OAK_INTO_LAB", 0x00),
        ("EVENT_OAK_ASKED_TO_CHOOSE_MON", 0x21),
        ("EVENT_GOT_STARTER", 0x22),
        ("EVENT_BATTLED_RIVAL_IN_OAKS_LAB", 0x23),
        ("EVENT_GOT_OAKS_PARCEL", 0x39),
        ("EVENT_GOT_POKEDEX", 0x25)
    ]


def test_each_term_reads_the_setting_named_for_it():
    """
    Asserts that each term pays the value of the setting its own value
    names, so no term reads another's setting.
    """
    settings = RewardSettings(goal=0.5, milestone=0.125, novelty=0.0625)

    assert {term: settings.pay(term) for term in Term} == {
        Term.GOAL      : 0.5,
        Term.MILESTONE : 0.125,
        Term.NOVELTY   : 0.0625
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


def test_the_settings_accept_a_goal_paying_more_than_every_other_term():
    """
    Asserts that a goal paying half again the milestone is accepted, so the
    goal has only to pay more than every other term.
    """
    assert RewardSettings(goal=0.1875, milestone=0.125).goal == 0.1875


@mark.parametrize(
    "settings",
    [
        param(
            {"goal": 0.5, "milestone": 0.125, "novelty": 0.125},
            id = "powers-of-two"
        ),
        param({"goal": 0.68, "milestone": 0.07, "novelty": 0.11}, id="decimals")
    ]
)
def test_the_ceiling_at_the_starter_sums_the_terms_without_rounding(
    settings: dict[str, float]
):
    """
    Asserts that a step reaching a new position and first setting every flag
    up to `EVENT_GOT_STARTER` at once earns exactly 1 under terms summing to
    1, whether each value is a power of two or a decimal whose sum one float
    addition at a time rounds to `1.0000000000000002`.
    """
    assert RewardSettings(**settings).ceiling(Event.EVENT_GOT_STARTER) == 1


@mark.parametrize(
    ("goal", "ceiling"),
    [
        param(Event.EVENT_OAK_APPEARED_IN_PALLET, 0.35025, id="the-first-flag"),
        param(Event.EVENT_GOT_STARTER, 0.65025, id="the-starter"),
        param(Event.EVENT_GOT_POKEDEX, 0.95025, id="the-pokedex")
    ]
)
def test_the_default_ceiling_counts_each_milestone_before_the_goal(
    ceiling : float,
    goal    : Event
):
    """
    Asserts that the default terms price a step reaching a new position and
    first setting every flag up to `goal` at once at the goal, the novelty,
    and a milestone for each flag before the goal, the six milestones before
    the Pokédex leaving it at 0.95025.
    """
    assert RewardSettings().ceiling(goal) == approx(ceiling)


@mark.parametrize(
    "settings",
    [
        param({"goal": 0.125, "milestone": 0.125}, id="level-with-a-milestone"),
        param({"goal": 0.125, "novelty": 0.25}, id="below-the-novelty")
    ]
)
def test_the_settings_refuse_a_goal_that_is_not_the_largest_term(
    settings: dict[str, float]
):
    """
    Asserts that a goal paying no more than a milestone or the novelty is
    refused, since the goal has to be the largest term.
    """
    with raises(ValidationError, match="where it has to be the largest term"):
        RewardSettings(**settings)


def test_the_total_sums_every_term_but_the_novelty(settings: RewardSettings):
    """
    Asserts that the reward for the flags a count of terms holds pays two
    milestones and the goal, leaving out the novelty it also counts.
    """
    assert settings.total({Term.GOAL: 1, Term.MILESTONE: 2, Term.NOVELTY: 5}) == 0.75
