"""
Pins how `Progress` scores each step of an episode, covering:

- The novelty a position earns the first time an episode reaches it, and
  nothing for a position it reached before or started on
- The milestone each flag earns once, on the step it first sets, and the
  starter, which ends the episode
- A flag already set when the episode starts, which earns nothing
- The share every term reports on every step, and the most one step earns
"""

from collections.abc import Callable
from operator        import attrgetter
from pytest          import mark, param

from squirtl.emulator.console import GameBoy
from squirtl.reward.progress  import Progress
from squirtl.reward.schemas   import Event, Position, RewardSettings, Score, Term


def earning(terminated: bool = False, **earned: float) -> Score:
    """
    Builds the score of a step that earned each term named in `earned` and
    nothing for every other term, ending the episode only where `terminated`
    is set.
    """
    return Score(shares=dict.fromkeys(Term, 0) | earned, terminated=terminated)


@mark.parametrize("field", Position.model_fields)
def test_a_step_reaching_a_new_position_earns_novelty_alone(
    field    : str,
    move     : Callable[[Position], None],
    progress : Progress,
    settings : RewardSettings
):
    """
    Asserts that a step moving the player onto a position the episode has
    not reached earns the novelty and nothing else, whichever of the map,
    the column, or the row tells it apart from the start.
    """
    move(Position(map=0, x=0, y=0).model_copy(update={field: 1}))

    assert progress.score() == earning(novelty=settings.novelty)


@mark.parametrize(
    "path",
    [
        param(
            [Position(map=0, x=0, y=0)],
            id = "staying-on-the-start"
        ),
        param(
            [Position(map=0, x=1, y=0), Position(map=0, x=0, y=0)],
            id = "returning-to-the-start"
        ),
        param(
            [Position(map=0, x=1, y=0), Position(map=0, x=2, y=0)] * 2,
            id = "retracing-a-path"
        )
    ]
)
def test_a_step_earns_nothing_for_a_position_the_episode_reached_before(
    move     : Callable[[Position], None],
    path     : list[Position],
    progress : Progress
):
    """
    Asserts that the last step of a path earns nothing where the episode
    already reached the position it ends on, whether the episode started
    there or a step reached it earlier.
    """
    for position in path:
        move(position)
        score = progress.score()

    assert score == earning()


@mark.parametrize(
    "event",
    [event for event in Event if event.term is Term.MILESTONE],
    ids = attrgetter("name")
)
def test_each_milestone_earns_once_on_the_step_its_flag_first_sets(
    event    : Event,
    flag     : Callable[[Event], None],
    progress : Progress,
    settings : RewardSettings
):
    """
    Asserts that the step first setting a milestone's flag earns the
    milestone term without ending the episode, and that a later step with
    the flag still set earns nothing.
    """
    flag(event)

    assert [
        progress.score(),
        progress.score()
    ] == [earning(milestone=settings.milestone), earning()]


@mark.parametrize("event", Event, ids=attrgetter("name"))
def test_a_flag_set_when_the_episode_starts_earns_nothing(
    event    : Event,
    flag     : Callable[[Event], None],
    game_boy : GameBoy,
    settings : RewardSettings
):
    """
    Asserts that a flag already set when the episode starts earns nothing
    and ends nothing, the starter's included, since no step of the episode
    set it.
    """
    flag(event)

    assert Progress(game_boy, settings).score() == earning()


def test_a_new_episode_earns_novelty_again_for_a_position_an_earlier_one_reached(
    game_boy : GameBoy,
    move     : Callable[[Position], None],
    progress : Progress,
    settings : RewardSettings
):
    """
    Asserts that the episode after one that reached a position earns the
    novelty once again on reaching it, since each episode records its own
    positions.
    """
    move(Position(map=0, x=1, y=0))
    progress.score()
    move(Position(map=0, x=0, y=0))
    restarted = Progress(game_boy, settings)
    move(Position(map=0, x=1, y=0))

    assert [
        restarted.score(),
        restarted.score()
    ] == [earning(novelty=settings.novelty), earning()]


def test_a_step_reaching_a_new_position_and_a_milestone_earns_both(
    flag     : Callable[[Event], None],
    move     : Callable[[Position], None],
    progress : Progress,
    settings : RewardSettings
):
    """
    Asserts that a step reaching a new position on the same step it first
    sets a milestone's flag earns both terms, the way stepping onto row 1 of
    Pallet Town, beside its north exit, sets `EVENT_OAK_APPEARED_IN_PALLET`.
    """
    move(Position(map=0, x=0, y=1))
    flag(Event.EVENT_OAK_APPEARED_IN_PALLET)

    assert progress.score() == earning(
        milestone = settings.milestone,
        novelty   = settings.novelty
    )


def test_the_most_one_step_earns_is_the_ceiling_the_settings_hold(
    flag     : Callable[[Event], None],
    move     : Callable[[Position], None],
    progress : Progress,
    settings : RewardSettings
):
    """
    Asserts that a step reaching a new position and first setting every flag
    at once earns the `ceiling` of its settings, which stays within 1, and
    ends the episode.
    """
    move(Position(map=0, x=1, y=0))

    for event in Event:
        flag(event)

    score = progress.score()

    assert (score.total, score.terminated) == (settings.ceiling, True)
    assert score.total <= 1


def test_the_starter_earns_its_term_and_ends_the_episode(
    flag     : Callable[[Event], None],
    progress : Progress,
    settings : RewardSettings
):
    """
    Asserts that the step first setting `EVENT_GOT_STARTER` earns the
    starter term and ends the episode.
    """
    flag(Event.EVENT_GOT_STARTER)

    assert progress.score() == earning(starter=settings.starter, terminated=True)


@mark.parametrize(
    "event",
    [event for event in Event if event.term is Term.MILESTONE],
    ids = attrgetter("name")
)
def test_a_milestone_whose_flag_clears_and_sets_again_earns_nothing_more(
    event    : Event,
    flag     : Callable[[Event], None],
    game_boy : GameBoy,
    progress : Progress
):
    """
    Asserts that a milestone earns once per episode, so a flag that clears,
    with every byte of memory, and then sets again earns nothing on the step
    it sets a second time.
    """
    flag(event)
    progress.score()
    memory    = game_boy.emulator.memory
    memory[:] = bytes(len(memory))
    progress.score()
    flag(event)

    assert progress.score() == earning()
