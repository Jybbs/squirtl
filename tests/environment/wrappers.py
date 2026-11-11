"""
Pins the wrappers `Overworld.specification` names beside Gymnasium's
own, covering:

- The mean `ShrinkObservation` takes over each square or oblong block of a
  frame small enough to average by hand, and the cells it shrinks a frame
  of PyBoy to at each block shape, which a reshape into blocks summed
  over each block also gives
- The `Outcome` `RecordOutcome` reports at an episode's last step alone,
  whether `TimeLimit` truncates the episode or the starter ends it
"""

from collections.abc    import Callable
from common.console     import set_event, stand
from gymnasium          import Env
from gymnasium.wrappers import RecordEpisodeStatistics, TimeLimit
from numpy              import array, ndarray, uint8, unique
from numpy.testing      import assert_array_equal
from pytest             import fixture, mark, param

from squirtl.environment.overworld import Overworld
from squirtl.environment.schemas   import Entry, Outcome, Snapshot
from squirtl.environment.wrappers  import RecordOutcome, ShrinkObservation
from squirtl.reward.schemas        import Event, Position, Term


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


@mark.parametrize(
    "shape",
    [
        param((72, 80),   id="blocks-of-2-by-2"),
        param((48, 32),   id="blocks-of-3-by-5"),
        param((144, 160), id="blocks-of-one-pixel"),
        param((1, 1),     id="one-block-of-the-whole-frame")
    ]
)
def test_a_frame_of_pyboy_shrinks_as_a_reshape_into_blocks_summed_shrinks_it(
    shaded : Overworld,
    shape  : tuple[int, int]
):
    """
    Asserts that a gray frame of PyBoy holding all four of its grays shrinks
    into the cells a reshape into `(height, rows, width, columns)` blocks
    gives once each block is summed, a half added, and the sum divided by
    the pixels each block holds, down to one block summing every pixel of
    the frame.
    """
    frame         = shaded.game_boy.grayscale
    height, width = shape
    blocks        = frame.reshape(height, 144 // height, width, 160 // width)
    pixels        = blocks.shape[1] * blocks.shape[3]

    assert unique(frame).tolist() == [0, 85, 153, 255]
    assert_array_equal(
        ShrinkObservation(shaded, shape).observation(frame),
        ((blocks.sum(axis=(1, 3)) + pixels // 2) // pixels).astype(uint8),
        strict = True
    )


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


def played_on(env: Env) -> tuple[dict[Entry, ndarray], Snapshot]:
    """
    Steps `env` twice.

    Returns:
        The observation its second step returns beside its capture there.
    """
    env.step(1)

    return env.step(2)[0], env.get_wrapper_attr("capture")()


def stepped(env: Env, presses: int) -> Env:
    """
    Resets `env` at seed 0 and steps it `presses` times with no press,
    leaving the stack holding those frames.

    Returns:
        The environment.
    """
    env.reset(seed=0)

    for _ in range(presses):
        env.step(0)

    return env


def test_a_restored_environment_plays_on_as_it_would_have(made: Callable[..., Env]):
    """
    Asserts that playing on from a restored snapshot reaches, byte for byte,
    the observation and the snapshot that playing straight on reaches, the
    emulator's state and every stacked frame among them.
    """
    env      = stepped(made(), 1)
    snapshot = env.get_wrapper_attr("capture")()
    straight = played_on(env)

    env.reset(options={"snapshot": snapshot})

    assert env.get_wrapper_attr("capture")() == snapshot

    replayed = played_on(env)

    assert replayed[1] == straight[1]

    for entry, values in straight[0].items():
        assert_array_equal(replayed[0][entry], values, err_msg=entry)


def test_a_snapshot_restores_into_a_fresh_environment(made: Callable[..., Env]):
    """
    Asserts that another environment on the same cartridge restores a
    snapshot and plays on to what the one capturing it reaches, as a worker
    process restoring what another played does.
    """
    first  = stepped(made(), 1)
    second = made()

    second.reset(options={"snapshot": first.get_wrapper_attr("capture")()})
    first.step(3)
    second.step(3)

    assert second.get_wrapper_attr("capture")() == first.get_wrapper_attr("capture")()


def test_a_snapshot_restores_the_episodes_progress(made: Callable[..., Env]):
    """
    Asserts that a restored environment holds the flags, the positions,
    and the shares of the step it was captured at, so its next step earns
    only what the episode has not, and that no press carries over into its
    record.
    """
    env       = stepped(made(), 2)
    overworld = env.unwrapped
    memory    = overworld.game_boy.emulator.memory

    stand(memory, Position(map=1, x=2, y=3))
    set_event(Event.EVENT_OAK_APPEARED_IN_PALLET, memory)
    env.step(0)

    snapshot = env.get_wrapper_attr("capture")()

    stand(memory, Position(map=9, x=9, y=9))
    set_event(Event.EVENT_GOT_STARTER, memory)
    env.step(0)

    observed, _ = env.reset(options={"snapshot": snapshot})

    assert overworld.progress.position == Position(map=1, x=2, y=3)
    assert overworld.progress.tally == snapshot.tally
    assert overworld.progress.events == {Event.EVENT_OAK_APPEARED_IN_PALLET}
    assert observed[Entry.FLAGS].sum() == 1
    assert overworld.timer_div == snapshot.timer_div
    assert bytes(overworld.actions) == b""


def test_a_snapshot_restores_the_observation_the_environment_held(
    made: Callable[..., Env]
):
    """
    Asserts that a reset given the snapshot of a step returns the stack, the
    flags, and the grid that step observed rather than a stack padded out
    of its newest frame, beside an empty info dict, and that the environment
    then captures that snapshot again.
    """
    env = made()

    env.reset(seed=0)
    observed, *_ = env.step(0)

    capture  = env.get_wrapper_attr("capture")
    snapshot = capture()

    for _ in range(5):
        env.step(0)

    restored, info = env.reset(options={"snapshot": snapshot})

    assert (capture(), info) == (snapshot, {})

    for entry, values in observed.items():
        assert_array_equal(restored[entry], values, err_msg=entry)


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
