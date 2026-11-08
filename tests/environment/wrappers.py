"""
Pins the wrappers `Overworld.specification` names beside Gymnasium's
own, covering:

- The mean `ShrinkObservation` takes over each square or oblong block of a
  frame small enough to average by hand, and the cells it shrinks a frame
  of PyBoy to at each block shape, which a reshape into blocks summed
  over each block also gives
- The `Outcome` and the `Recording` `RecordOutcome` reports at an episode's
  last step alone, whether `TimeLimit` truncates the episode or the starter
  ends it
- The unfinished episode `ReplayRecording` plays back at the next reset alone,
  which leaves the wrappers beneath it where the recording's last step left
  them
- The segments `FollowDemonstration` splits a demonstration into at each
  flag, the demonstration it refuses, the start each reset draws from the
  windows it is given and the frames it observes there, the success and the
  limit that truncate an episode from a start, and the takeover a resumed
  run plays back
"""

from collections.abc    import Callable
from common.console     import set_event
from gymnasium          import Env
from gymnasium.wrappers import RecordEpisodeStatistics, TimeLimit
from numpy              import array, uint8, unique
from numpy.random       import default_rng
from numpy.testing      import assert_array_equal
from pytest             import fixture, mark, param, raises

from squirtl.environment.overworld import Overworld
from squirtl.environment.schemas   import Entry, Outcome, Recording, Starts, Takeover, Window
from squirtl.environment.wrappers  import FollowDemonstration, RecordOutcome, ShrinkObservation
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
    assert ["recording" in info for info in infos] == [False, False, True]
    assert (infos[-1]["recording"].presses, infos[-1]["recording"].timer_div) == (
        bytes([0, 0, 0]),
        recorded.get_wrapper_attr("recording").timer_div
    )
    assert infos[-1]["outcome"] == Outcome(
        length     = 3,
        positions  = 4,
        reward     = 0.1875,
        seconds    = infos[-1]["episode"]["t"],
        shares     = {Term.MILESTONE: 0.0, Term.NOVELTY: 0.1875, Term.STARTER: 0.0},
        terminated = False
    )


def start(
    *,
    earliest : int,
    env      : Env,
    latest   : int,
    segment  : int,
    limit    : int = 50
) -> dict:
    """
    Sets on `env` the one window of `segment` from `earliest` to `latest`
    under `limit`, then resets it at a seed of 0.

    Returns:
        The observation the reset ends on.
    """
    window = Window(earliest=earliest, latest=latest, segment=segment)
    env.set_wrapper_attr("starts", Starts(limit=limit, windows=[window]))

    return env.reset(seed=0)[0]


def test_a_demonstration_splits_into_a_segment_at_each_flag_it_sets(
    following: Callable[..., Env]
):
    """
    Asserts that the demonstration of 13 presses splits at the presses at
    steps 4, 8, and 12, each setting one more flag of the cartridge's, after
    keeping a state, a stack of frames, and the terms earned before each
    press.
    """
    env = following()

    assert env.get_wrapper_attr("ends") == [4, 8, 12]
    assert [len(env.get_wrapper_attr(name)) for name in (
        "states", "stacks", "earned"
    )] == [
        13, 13, 14
    ]


def test_a_reset_plays_a_recording_back_through_every_wrapper_beneath_it(
    made: Callable[..., Env]
):
    """
    Asserts that an environment on PyBoy given the recording of three
    steps of an unfinished episode observes at its next reset what a copy
    that played those steps observes, then truncates when that copy does,
    its time limit counting the replayed steps, with its outcome and its
    recording reporting the whole episode, and that the reset after it plays
    nothing back.
    """
    played, replaying = made(max_episode_steps=5), made(max_episode_steps=5)
    played.reset(seed=0)
    actions = default_rng(0).integers(played.action_space.n, size=5).tolist()

    for action in actions[:3]:
        observed, *_ = played.step(action)

    replaying.reset(seed=1)
    replaying.set_wrapper_attr("resumed", played.get_wrapper_attr("recording"))
    replayed, info = replaying.reset()

    assert info == {}
    assert replaying.get_wrapper_attr("resumed") is None
    assert_array_equal(replayed["frames"], observed["frames"])
    assert_array_equal(replayed["flags"], observed["flags"])

    endings = [
        (
            env.step(actions[3])[3:],
            env.step(actions[4])[3:]
        ) for env in (played, replaying)
    ]

    assert endings[0][0][0] is endings[1][0][0] is False
    assert endings[0][1][0] is endings[1][1][0] is True
    assert endings[0][1][1]["recording"] == endings[1][1][1]["recording"]
    assert endings[1][1][1]["outcome"].length == 5

    replaying.reset(seed=1)

    assert replaying.get_wrapper_attr("recording").presses == b""


def test_a_reset_with_no_starts_begins_in_the_bedroom(following: Callable[..., Env]):
    """
    Asserts that with no starts set, a reset starts in the bedroom at the
    `timer_div` its seed draws, and the episode reports no success at its
    end.
    """
    env = following()
    env.reset(seed=0)

    assert env.get_wrapper_attr("recording") == Recording(
        presses   = b"",
        timer_div = default_rng(0).integers(256)
    )

    terminated = truncated = False

    while not (terminated or truncated):
        *_, terminated, truncated, info = env.step(0)

    assert (terminated, "succeeded" in info) == (True, False)


@mark.parametrize(
    "presses",
    [param(bytes(12), id="short-of-the-starter"), param(bytes(14), id="past-it")]
)
def test_a_demonstration_not_reaching_the_starter_at_its_last_press_is_refused(
    following : Callable[..., Env],
    presses   : bytes
):
    """
    Asserts that a demonstration stopping short of the starter, or holding
    presses past the one reaching it, is refused as the wrapper plays it.
    """
    with raises(ValueError, match="no longer reach the starter"):
        following(presses)


def test_a_start_falling_short_by_less_than_the_tolerance_succeeds(
    following: Callable[..., Env]
):
    """
    Asserts that under a tolerance of a milestone, an episode from a start
    whose segment pays one succeeds at its first step.
    """
    env = following(tolerance=0.1)
    start(
        earliest = 0,
        env      = env,
        latest   = 0,
        segment  = 0
    )
    *_, truncated, info = env.step(0)

    assert (truncated, info["succeeded"]) == (True, True)


def test_a_start_observes_the_frames_the_demonstration_stacked_there(
    following: Callable[..., Env]
):
    """
    Asserts that a start at step 6 observes the frames and the flags the
    demonstration observed there, leaving those frames in the stack the next
    step pushes onto.
    """
    env      = following()
    observed = start(
        earliest = 6,
        env      = env,
        latest   = 6,
        segment  = 1
    )
    stack = env.get_wrapper_attr("stacks")[6]

    assert_array_equal(observed[Entry.FRAMES], stack, strict=True)
    assert observed[Entry.FLAGS].tolist() == [[0, 0, 1, 0]]

    stepped, *_ = env.step(0)

    assert_array_equal(stepped[Entry.FRAMES][:-1], stack[1:], strict=True)


def test_a_takeover_plays_back_as_the_episode_it_left_unfinished(
    following: Callable[..., Env]
):
    """
    Asserts that an environment given the recording of an unfinished episode
    from a start resumes it at its next reset, observing what the episode
    observed and ending where it ends, whatever starts it holds.
    """
    played, replaying = following(), following()
    start(
        earliest = 5,
        env      = played,
        latest   = 5,
        segment  = 1
    )

    for _ in range(2):
        observed, *_ = played.step(0)

    replaying.set_wrapper_attr("resumed", played.get_wrapper_attr("recording"))
    replayed, _ = replaying.reset()

    assert_array_equal(replayed[Entry.FLAGS], observed[Entry.FLAGS])
    assert replaying.get_wrapper_attr("takeover") == Takeover(
        limit     = 50,
        segment   = 1,
        step      = 5,
        timer_div = played.get_wrapper_attr("takeover").timer_div
    )
    assert [env.step(0)[2:4] for env in (played, replaying)] == [(False, False)] * 2
    assert [env.step(0)[2:4] for env in (played, replaying)] == [(False, True)] * 2


@mark.parametrize(
    ("segment", "step", "limit", "length", "ended"),
    [
        param(0, 2, 50, 3, (False, True, True),  id="succeeding-at-a-flag"),
        param(2, 10, 50, 3, (True, False, True), id="reaching-the-starter"),
        param(0, 0, 2, 2, (False, True, False),  id="at-its-limit")
    ]
)
def test_a_start_ends_once_it_succeeds_or_reaches_its_limit(
    ended     : tuple[bool, bool, bool],
    following : Callable[..., Env],
    length    : int,
    limit     : int,
    segment   : int,
    step      : int
):
    """
    Asserts that an episode from a start ends at the step setting its
    segment's flag, truncated short of the starter and terminated at it,
    or at its limit, reporting whether it succeeded and recording the
    demonstration's presses before its own.
    """
    env = following()
    start(
        earliest = step,
        env      = env,
        latest   = step,
        limit    = limit,
        segment  = segment
    )
    steps = [env.step(0) for _ in range(length)]
    *_, terminated, truncated, info = steps[-1]

    assert [any(taken[2:4]) for taken in steps] == [False] * (length - 1) + [True]
    assert (terminated, truncated, info["succeeded"]) == ended
    assert info["outcome"].length == length
    assert info["recording"].takeover.step == step
    assert info["recording"].presses == bytes(step + length)


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


def test_each_start_draws_its_segment_step_and_div_from_the_windows(
    following: Callable[..., Env]
):
    """
    Asserts that resets with no seed after a seeded one draw each start's
    segment among the windows set, its step within that segment's window,
    and its `timer_div` from the environment's generator, the seed repeating
    the draws.
    """
    env     = following()
    windows = [
        Window(earliest=0, latest=3, segment=0),
        Window(earliest=9, latest=11, segment=2)
    ]
    env.set_wrapper_attr("starts", Starts(limit=50, windows=windows))
    drawn = []

    for seed in (3, *[None] * 30, 3):
        env.reset(seed=seed)
        drawn.append(env.get_wrapper_attr("takeover"))

    assert drawn[0] == drawn[-1]
    assert {(
        takeover.segment,
        takeover.step in range(
            windows[takeover.segment // 2].earliest,
            windows[takeover.segment // 2].latest + 1
        )
    ) for takeover in drawn} == {(0, True), (2, True)}
    assert len({takeover.timer_div for takeover in drawn}) > 1


def test_the_wrapper_sits_where_the_specification_names_it(
    following: Callable[..., Env]
):
    """
    Asserts that `FollowDemonstration` wraps `ProgressObservation` beneath
    `RecordEpisodeStatistics`, so the statistics count an episode's own
    steps alone.
    """
    assert isinstance(following().env.env.env, FollowDemonstration)
