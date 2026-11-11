"""
Pins the search over particles, Mhammedi and Cohan's Algorithms 1 and
2, covering:

- Every particle starting on the root, and the group's winner
- One outer step, where each survivor adds a child, each dead particle
  moves to the winner, and every particle rolls back once all are dead
- A state kept only where a particle moves to another's node
- One iteration, where a group below the winner on reward moves to it, each
  group consolidates on its winner, and the best of those and the last
  winner, scored afresh, becomes the winner
- The search ending at its goal, and on no other flag, or at its steps
- Each rollout's presses, one action held at the chance of a random one
- One seed reaching one demonstration, whichever order the rollouts play
  in, a search resumed from its checkpoint going on as an unbroken one does,
  and the demonstration playing back to what the winner reached
"""

from collections.abc import Callable, Iterable
from common.search   import assert_same_checkpoint, drive, ending, particle, searched, snapshot
from gymnasium       import Env
from numpy           import frombuffer, uint8
from pathlib         import Path
from pytest          import MonkeyPatch, mark, param, raises
from torch.testing   import assert_close

from squirtl.environment.overworld import Overworld
from squirtl.environment.schemas   import Recording, Snapshot
from squirtl.reward.schemas        import Event
from squirtl.search.checkpoint     import SearchCheckpoint
from squirtl.search.particles      import Group, Search
from squirtl.search.schemas        import Ending, Particle, Rollout
from squirtl.search.workers        import roll

type Script = Callable[..., Callable[[Iterable[Rollout]], Iterable[Ending]]]


def in_reverse(rollouts: Iterable[Rollout]) -> list[Ending]:
    """
    Plays `rollouts` from the last to the first, returning each ending in
    the order submitted, as workers finishing out of order do.
    """
    return [*map(roll, reversed([*rollouts]))][::-1]


def scored(monkeypatch: MonkeyPatch, search: Search, *scores: float):
    """
    Makes the predictor of `search` score each snapshot in turn with the
    next of `scores`.
    """
    remaining = iter(scores)

    monkeypatch.setattr(
        search.novelty,
        "score",
        lambda snapshots: [next(remaining) for _ in snapshots]
    )


def test_a_dead_particle_moves_to_the_survivor_ranking_highest_and_its_state_is_kept(
    monkeypatch : MonkeyPatch,
    rolled      : Script,
    searching   : Callable[..., Search]
):
    """
    Asserts that a dead particle adds no child and moves to the survivor
    with the most reward, then the highest score, whose state the tree keeps
    since a particle moved to it, and that the dead rollout's presses count.
    """
    search = searching(
        rolled([ending(dead=True), ending(x=1), ending(x=2), ending(reward=0.1, x=3)]),
        groups    = 1,
        particles = 4
    )

    scored(monkeypatch, search, 9.0, 0.5, 0.1)
    search.step(search.groups)

    winner = search.groups[0].winner

    assert [held.node for held in search.groups[0].particles] == [3, 1, 2, 3]
    assert (winner.reward, winner.score, len(search.tree)) == (0.1, 0.1, 4)
    assert ([*search.tree.states], search.presses) == ([0, 3], 4)


def test_a_group_below_the_winner_on_reward_moves_to_it_as_an_iteration_opens(
    rolled    : Script,
    searching : Callable[..., Search]
):
    """
    Asserts that a group whose winner has less reward than the search's
    winner moves to it as an iteration opens, whereas a group holding the
    same reward stays with its particles.
    """
    search = searching(
        rolled([ending(presses=b"\x01", x=n) for n in range(32)]),
        outer_steps = (1, 1)
    )

    for _ in range(8):
        search.tree.add(0, b"\x01")

    search.groups[0].reset(particle(5, 0.0, 9.0))
    search.groups[1].reset(particle(8, 0.1, 0.1))
    search.winner = particle(7, 0.1, 0.5)

    played = []
    roller = search.roll

    def spy(rollouts: Iterable[Rollout]) -> Iterable[Ending]:
        """
        Records the node of each rollout's start through its snapshot.
        """
        rollouts = [*rollouts]
        played.extend(rollout.snapshot.tally.position.x for rollout in rollouts)

        return roller(rollouts)

    search.roll = spy
    drive(search)

    assert played == [7, 7, 8, 8]


def test_a_group_reset_moves_every_particle_to_one():
    """
    Asserts that a reset leaves every particle of the group on the one it
    names, keeping their count.
    """
    group = Group(particle(), 3)
    held  = particle(5)

    group.reset(held)

    assert group.particles == [held] * 3


def test_a_group_winner_is_the_first_of_those_ranking_highest():
    """
    Asserts that a group's winner has the most reward, then the highest
    score, and the first place among those tied.
    """
    group = Group(particle(), 4)

    group.particles = [
        particle(1, 0.0, 9.0),
        particle(2, 0.1, 0.5),
        particle(3, 0.1, 0.7),
        particle(4, 0.1, 0.7)
    ]

    assert group.winner.node == 3


def test_a_group_winner_with_more_reward_becomes_the_winner(
    rolled    : Script,
    searching : Callable[..., Search]
):
    """
    Asserts that a group's winner with more reward than the last winner
    becomes the winner, whose path is what the demonstration holds.
    """
    search = searching(
        rolled(
            [
                ending(presses=b"\x01", x=1),
                ending(presses=b"\x02", x=2),
                ending(presses=b"\x03", reward=0.1, x=3),
                ending(presses=b"\x04", x=4)
            ]
        ),
        outer_steps = (1, 1)
    )

    drive(search)

    assert (search.winner.reward, search.demonstration.presses) == (0.1, b"\x03")
    assert search.demonstration.timer_div == 3


def test_a_rollback_past_the_root_stops_at_it(
    rolled    : Script,
    searching : Callable[..., Search]
):
    """
    Asserts that a group dying on the root moves back to the root however
    far `rollback` draws, the worker bringing it back with no press.
    """
    played = []
    search = searching(
        rolled([ending(dead=True), ending(dead=True), ending(presses=b"")], played),
        groups   = 1,
        rollback = (3, 3)
    )

    search.step(search.groups)

    assert [held.node for held in search.groups[0].particles] == [0, 0]
    assert (played[-1].presses, len(played), search.presses) == (b"", 3, 2)


def test_a_rollout_bringing_back_a_node_counts_no_press(
    rolled    : Script,
    searching : Callable[..., Search]
):
    """
    Asserts that only the rollouts a group plays forward count as presses,
    so replaying a node's presses spends none of the run's `steps`.
    """
    search = searching(
        rolled(
            [
                ending(presses=b"\x01\x02", x=1),
                ending(presses=b"\x01\x02", x=2),
                ending(dead=True, presses=b"\x03"),
                ending(dead=True, presses=b"\x03"),
                ending(presses=b"\x01\x02", x=1),
                ending(presses=b"\x01\x02", x=2)
            ]
        ),
        groups   = 1,
        rollback = (1, 1)
    )

    search.step(search.groups)
    search.step(search.groups)

    assert search.presses == 6


def test_a_rollouts_press_rate_leaves_the_held_action_at_the_paper_chance(
    rolled    : Script,
    searching : Callable[..., Search]
):
    """
    Asserts that at the default chance of 0.2, the action a rollout holds
    fills between 70% and 90% of its presses.
    """
    search  = searching(rolled([]), epsilon=0.2, inner_steps=(2_000, 2_000))
    presses = frombuffer(search.plan(), uint8)
    shares  = sorted(((presses == action).mean() for action in range(7)), reverse=True)

    assert 0.7 < shares[0] < 0.9


def test_a_rollouts_presses_count_within_the_inner_steps(
    rolled    : Script,
    searching : Callable[..., Search]
):
    """
    Asserts that a rollout's presses count every value of `inner_steps`,
    both ends included, and nothing outside them.
    """
    search = searching(rolled([]))

    assert {len(search.plan()) for _ in range(100)} == {2, 3, 4}


def test_an_iteration_ends_at_the_starter_on_the_particle_holding_it(
    rolled    : Script,
    searching : Callable[..., Search]
):
    """
    Asserts that the outer step setting the flag ends the iteration, however
    many outer steps remain, with that particle the winner.
    """
    search = searching(
        rolled(
            [
                ending(x=1),
                ending(x=2),
                ending(events=(Event.EVENT_GOT_STARTER,), reward=0.6, x=3),
                ending(x=4)
            ]
        ),
        outer_steps = (9, 9)
    )

    drive(search)

    assert search.reached and search.finished


def test_consolidating_drops_each_state_no_particle_can_reach(
    rolled    : Script,
    searching : Callable[..., Search]
):
    """
    Asserts that an iteration's end leaves only the states on a lineage of a
    group's winner or of the search's winner, the root's among them.
    """
    search = searching(
        rolled([ending(x=n) for n in range(4)]),
        outer_steps = (1, 1)
    )
    stray = search.tree.add(0, b"\x05")

    search.tree.states[stray] = snapshot(x=9)
    drive(search)

    assert stray not in search.tree.states and 0 in search.tree.states


@mark.parametrize(
    ("steps", "events", "finished"),
    [
        param(100, (), False, id="neither"),
        param(4, (), True, id="the-steps"),
        param(100, (Event.EVENT_GOT_STARTER,), True, id="the-starter"),
        param(100, (Event.EVENT_OAK_APPEARED_IN_PALLET,), False, id="a-milestone")
    ]
)
def test_a_search_finishes_at_its_steps_or_the_starter(
    events    : tuple[Event, ...],
    finished  : bool,
    rolled    : Script,
    searching : Callable[..., Search],
    steps     : int
):
    """
    Asserts that a search finishes once its presses reach `steps` or a
    particle holds `EVENT_GOT_STARTER`, and on neither otherwise.
    """
    search = searching(
        rolled(
            [
                ending(presses=b"\x01\x01", x=1),
                ending(presses=b"\x01\x01", x=2),
                ending(events=events, x=3),
                ending(x=4)
            ]
        ),
        outer_steps = (9, 9),
        steps       = steps
    )

    search.groups[0].remaining = 1
    search.step(search.groups)

    assert search.finished is finished


def test_each_group_plays_only_while_it_has_outer_steps_left(
    monkeypatch : MonkeyPatch,
    searching   : Callable[..., Search]
):
    """
    Asserts that one iteration plays each group for the outer steps it drew
    and no more, and that each group consolidates at the end.
    """
    played = []

    def play(rollouts: Iterable[Rollout]) -> list[Ending]:
        """
        Records how many rollouts each outer step submits.
        """
        rollouts = [*rollouts]
        played.append(len(rollouts))

        return [ending(x=len(played)) for _ in rollouts]

    search = searching(play, outer_steps=(1, 2))
    draws  = iter([1, 2])

    monkeypatch.setattr(
        search,
        "draw",
        lambda bounds: next(draws) if bounds == (1, 2) else 2
    )
    drive(search)

    assert played == [4, 2]
    assert all(
        len({held.node for held in group.particles}) == 1 for group in search.groups
    )


@mark.parametrize(
    ("epsilon", "distinct"),
    [param(0.0, 1, id="never-random"), param(1.0, 7, id="always-random")]
)
def test_a_rollouts_presses_hold_one_action_at_the_chance_of_a_random_one(
    distinct  : int,
    epsilon   : float,
    rolled    : Script,
    searching : Callable[..., Search]
):
    """
    Asserts that at a chance of 0 a rollout's presses hold one action, and
    that at a chance of 1 they range over every action.
    """
    search = searching(rolled([]), epsilon=epsilon, inner_steps=(200, 200))

    assert len(set(search.plan())) == distinct


def test_each_survivor_adds_a_child_holding_its_presses_and_no_state_is_kept(
    monkeypatch : MonkeyPatch,
    rolled      : Script,
    searching   : Callable[..., Search]
):
    """
    Asserts that where no particle dies, each ending adds a child of its
    particle's node reached by its presses, each particle moves there, and
    the tree keeps no state beyond the root's, since no particle moved to
    another's node.
    """
    search = searching(
        rolled([ending(presses=b"\x01", x=1), ending(presses=b"\x02\x02", x=2)]),
        groups = 1
    )

    scored(monkeypatch, search, 0.1, 0.2)
    search.step(search.groups)

    assert [held.node for held in search.groups[0].particles] == [1, 2]
    assert (search.tree.path(1), search.tree.path(2)) == (b"\x01", b"\x02\x02")
    assert ([*search.tree.states], search.presses) == ([0], 3)


def test_every_dead_particle_rolls_back_to_an_ancestor_brought_back_from_a_kept_state(
    monkeypatch : MonkeyPatch,
    rolled      : Script,
    searching   : Callable[..., Search]
):
    """
    Asserts that once every particle of a group is dead, each moves the
    generations `rollback` draws above its node, and that a worker brings
    the ancestor back from the nearest kept state, playing on past any
    reward, with the tree then keeping that ancestor's state.
    """
    restored = ending(presses=b"\x01", reward=0.1, x=5)
    played   = []
    search   = searching(
        rolled(
            [
                ending(presses=b"\x01", x=1),
                ending(presses=b"\x02", x=2),
                ending(presses=b"\x03", x=3),
                ending(presses=b"\x04", x=4),
                ending(dead=True),
                ending(dead=True),
                restored
            ],
            played
        ),
        groups   = 1,
        rollback = (1, 1)
    )

    scored(monkeypatch, search, 0.1, 0.2, 0.3, 0.4, 0.7)
    search.step(search.groups)
    search.step(search.groups)

    particles = search.groups[0].particles
    search.groups[0].particles = [particles[0], particles[0]]
    search.step(search.groups)

    node = search.tree.parents[particles[0].node]

    assert [held.node for held in search.groups[0].particles] == [node, node]
    assert search.groups[0].winner.reward == 0.1
    assert (played[-1].halting, played[-1].snapshot) == (False, search.tree.states[0])
    assert search.tree.states[node] == restored.snapshot


def test_every_particle_of_a_new_search_starts_on_the_root(
    rolled    : Script,
    searching : Callable[..., Search]
):
    """
    Asserts that each group of a new search holds its count of particles on
    node 0, with no reward, and that the root is the winner.
    """
    search = searching(rolled([]))

    assert [group.particles for group in search.groups] == [[search.winner] * 2] * 2
    assert (search.winner.node, search.winner.reward, len(search.tree)) == (0, 0.0, 1)


@mark.usefixtures("game")
def test_one_seed_finds_one_demonstration_whichever_order_the_rollouts_play_in(
    root      : Snapshot,
    rolling   : Callable[[Iterable[Rollout]], Iterable[Ending]],
    searching : Callable[..., Search]
):
    """
    Asserts that a search playing its rollouts in reverse reaches the
    demonstration, the tree, and the predictor's weights of one playing them
    in order, and that another seed reaches another.
    """
    first, second, other = (
        searched(searching(play, root=root, seed=seed, steps=150))
        for play, seed in ((rolling, 7), (in_reverse, 7), (rolling, 8))
    )

    assert first.demonstration == second.demonstration != other.demonstration
    assert first.tree.path(len(first.tree) - 1) == second.tree.path(
        len(second.tree) - 1
    )
    assert_close(
        first.novelty.predictor.state_dict(),
        second.novelty.predictor.state_dict(),
        atol = 0,
        rtol = 0
    )


@mark.usefixtures("game")
def test_a_search_resumed_from_its_checkpoint_goes_on_as_an_unbroken_one_does(
    root      : Snapshot,
    rolling   : Callable[[Iterable[Rollout]], Iterable[Ending]],
    searching : Callable[..., Search],
    tmp_path  : Path
):
    """
    Asserts that a search written to its checkpoint after two iterations
    and read back into a new search built from another seed plays on to the
    demonstration, tree, frontier, and networks of one that never stopped.
    """
    path     = tmp_path / "checkpoint.npz"
    unbroken = searching(rolling, root=root, steps=150)

    stopped = searching(rolling, root=root, steps=150)
    drive(stopped)
    drive(stopped)
    stopped.checkpoint.save(path)

    resumed = searching(rolling, root=root, seed=9, steps=150)
    resumed.restore(SearchCheckpoint.from_path(path))

    searched(unbroken)
    searched(resumed)

    assert_same_checkpoint(unbroken.checkpoint, resumed.checkpoint)


@mark.usefixtures("game")
def test_a_restore_of_another_capacity_is_refused(
    rolled    : Script,
    root      : Snapshot,
    rolling   : Callable[[Iterable[Rollout]], Iterable[Ending]],
    searching : Callable[..., Search],
    tmp_path  : Path
):
    """
    Asserts that a checkpoint whose replay memory holds other arrays than
    the search it loads into builds raises rather than running on them.
    """
    path = tmp_path / "checkpoint.npz"

    searched(searching(rolling, root=root, steps=10)).checkpoint.save(path)

    with raises(ValueError):
        searching(rolled([]), capacity=128).restore(SearchCheckpoint.from_path(path))


@mark.usefixtures("game")
def test_the_demonstration_plays_back_to_what_the_winner_reached(
    booted    : Env,
    root      : Snapshot,
    rolling   : Callable[[Iterable[Rollout]], Iterable[Ending]],
    searching : Callable[..., Search]
):
    """
    Asserts that a search running to the starter leaves a demonstration that
    plays from the reset at its `timer_div` to the flag, the reward, and the
    position the winner's snapshot holds, and that no press past the flag
    follows it.
    """
    search = searched(searching(rolling, root=root))
    winner = search.winner
    played = booted.unwrapped

    assert isinstance(search.demonstration, Recording) and isinstance(played, Overworld)
    assert search.reached

    played.play(search.demonstration)

    assert played.reward.total(played.progress.earned) == winner.reward
    assert played.progress.position == winner.snapshot.tally.position
    assert Event.EVENT_GOT_STARTER in played.progress.events


def test_the_winner_is_the_best_of_the_groups_and_the_last_one_scored_afresh(
    monkeypatch : MonkeyPatch,
    rolled      : Script,
    searching   : Callable[..., Search]
):
    """
    Asserts that a last winner still holding the most reward stays the
    winner under the score the predictor now gives it, ranking above each
    group's consolidated winner, and that the states of its lineage stay in
    the tree.
    """
    search = searching(
        rolled([ending(presses=b"\x01", x=n) for n in range(4)]),
        outer_steps = (1, 1)
    )
    node  = search.tree.add(0, b"\x05")
    state = snapshot(x=9)

    search.tree.states[node] = state

    search.winner = Particle(
        node     = node,
        reward   = 0.1,
        score    = 0.9,
        snapshot = state
    )

    for group in search.groups:
        group.reset(search.winner)

    scored(monkeypatch, search, 0.1, 0.2, 0.3, 0.4, 0.05)
    drive(search)

    assert (
        search.winner.node, search.winner.score, search.iterations
    ) == (node, 0.05, 1)
    assert node in search.tree.states


@mark.parametrize(
    ("goal", "events", "finished"),
    [
        param(Event.EVENT_GOT_STARTER, (), False, id="no-flag"),
        param(
            Event.EVENT_GOT_STARTER,
            (Event.EVENT_OAK_APPEARED_IN_PALLET,),
            False,
            id = "a-milestone"
        ),
        param(Event.EVENT_GOT_STARTER, (Event.EVENT_GOT_STARTER,), True, id="the-goal"),
        param(
            Event.EVENT_GOT_POKEDEX,
            (Event.EVENT_GOT_STARTER,),
            False,
            id = "a-flag-short-of-a-later-goal"
        )
    ]
)
def test_a_search_finishes_on_a_particle_setting_its_goal_alone(
    events    : tuple[Event, ...],
    finished  : bool,
    goal      : Event,
    rolled    : Script,
    searching : Callable[..., Search]
):
    """
    Asserts that a search reads as finished once a particle's snapshot holds
    the run's goal, and on no other flag, whichever goal the run names.
    """
    search = searching(rolled([]), goal=goal)
    search.groups[0].particles[0] = particle(events=events)

    assert search.finished is finished
