"""
Pins the curriculum moving each segment's window along a
demonstration, covering:

- The windows each segment starts at, the window's span, the bedroom no
  window starts before, and the limit before and after a success
- The move back at the required share and forward below it, by a multiple
  of the window drawn between the bounds the settings give, held between
  the bedroom and the segment's end, and the count starting again after
  each move
- A segment solved at the bedroom once its share reaches the completion
  share, leaving the windows of the rest, and no window once every one is
- An episode drawn before its window's last move left out of the share
- The line logged at each move, the moving average of successful lengths,
  a curriculum restored from its syllabus drawing as the one it was taken
  from, and a syllabus whose segments end elsewhere refused
"""

from numpy.random import default_rng
from pytest       import approx, mark, param, raises

from squirtl.environment.schemas import Starts, Takeover, Window
from squirtl.runs.curriculum     import Curriculum, Segment
from squirtl.runs.settings       import CurriculumSettings


def attempt(curriculum: Curriculum, number: int, *outcomes: bool, length: int = 10):
    """
    Has `curriculum` take in an episode of `length` steps drawn from the
    window of segment `number` as it stands for each of `outcomes`, each
    whether it succeeded.
    """
    for succeeded in outcomes:
        curriculum.attempted(
            length    = length,
            succeeded = succeeded,
            takeover  = taken(curriculum, number)
        )


def build(**fields: object) -> Curriculum:
    """
    Builds the curriculum of segments ending at steps 40 and 90, seeded at
    0, its settings counting the share over four episodes, any keyword a
    field of `CurriculumSettings` to set in its place.
    """
    return Curriculum(
        [40, 90],
        0,
        CurriculumSettings.model_validate({"recent": 4} | fields)
    )


def taken(curriculum: Curriculum, number: int) -> Takeover:
    """
    Builds a takeover at the bedroom from the window of segment `number` as
    it stands, carrying the moves that window has taken.
    """
    return Takeover(
        limit     = curriculum.limit,
        moves     = curriculum.segments[number].moves,
        segment   = number,
        step      = 0,
        timer_div = 0
    )


def test_a_curriculum_restored_from_its_syllabus_moves_as_the_one_taken_from():
    """
    Asserts that a curriculum restored from another's syllabus holds its
    segments and its moving average and draws each move as that one does.
    """
    curriculum, restored = build(), build()
    attempt(curriculum, 1, True, True, length=12)
    restored.restore(curriculum.syllabus)

    for each in (curriculum, restored):
        attempt(each, 1, True, True)
        attempt(each, 0, *[True] * 4)

    assert restored.syllabus == curriculum.syllabus


@mark.parametrize(
    ("outcomes", "latest"),
    [
        param(
            (True, False, False, False),
            40 - round(default_rng(0).uniform(0.25, 0.75) * 25),
            id = "back-at-the-required-share"
        ),
        param((False,) * 4, 40,                     id="forward-held-at-the-end")
    ]
)
def test_a_window_moves_once_its_recent_episodes_fill(
    latest   : int,
    outcomes : tuple[bool, ...]
):
    """
    Asserts that a window holds until its recent episodes number the four
    the settings count, then moves back where a quarter succeeded, reaching
    the required share, by a multiple of the window the generator draws
    between the decrease bounds, or forward where none did, held at the
    segment's end, and starts its count again.
    """
    curriculum = build()
    attempt(curriculum, 0, *outcomes[:3])

    assert curriculum.segments[0].latest == 40

    attempt(curriculum, 0, outcomes[3])

    assert curriculum.segments[0] == Segment(
        end    = 40,
        latest = latest,
        moves  = 1,
        recent = [],
        solved = False
    )


def test_a_curriculum_with_every_segment_solved_gives_no_starts():
    """
    Asserts that once every segment is solved, the curriculum gives no
    starts, and that an episode still in flight from a solved segment
    changes nothing.
    """
    curriculum = build(back=(4.0, 4.0))

    for number in (0, 1):
        attempt(curriculum, number, *[True] * 8)

    attempt(curriculum, 0, False)

    assert (curriculum.starts, curriculum.segments[0].recent) == (None, [])


def test_a_syllabus_whose_segments_end_elsewhere_is_refused():
    """
    Asserts that restoring a syllabus whose segments end at other steps than
    the curriculum's raises, naming both lists of ends.
    """
    taken_from = Curriculum([40, 91], 0, CurriculumSettings())

    with raises(
        ValueError,
        match = r"end at steps \[40, 91\], .* end at steps \[40, 90\]"
    ):
        build().restore(taken_from.syllabus)


@mark.parametrize(
    ("share", "solved", "windows"),
    [
        param(4, True, [1], id="at-the-completion-share"),
        param(3, False, [0, 1], id="short-of-it")
    ]
)
def test_a_segment_at_the_bedroom_is_solved_at_the_completion_share(
    share   : int,
    solved  : bool,
    windows : list[int]
):
    """
    Asserts that a segment whose window starts at the bedroom counts as
    solved once every one of its four recent episodes succeeds, reaching the
    completion share of 0.95, after which its window leaves the starts, and
    that three successes leave it where it is.
    """
    curriculum = build(back=(2.0, 2.0))
    attempt(curriculum, 0, *[True] * 4)
    attempt(curriculum, 0, *[True] * share, *[False] * (4 - share))

    assert (curriculum.segments[0].solved, curriculum.segments[0].latest) == (solved, 0)
    assert [window.segment for window in curriculum.starts.windows] == windows


def test_a_window_moves_by_a_multiple_of_the_window_between_its_bounds():
    """
    Asserts that each move draws its size uniformly between the bounds the
    settings give, times the window, so bounds of one move by exactly the
    window, back from the end and then forward again.
    """
    curriculum = build(back=(1.0, 1.0), forward=(1.0, 1.0), window=10)
    latest     = []

    for outcome in (True, True, False):
        attempt(curriculum, 1, *[outcome] * 4)
        latest.append(curriculum.segments[1].latest)

    assert latest == [80, 70, 80]


def test_a_window_moving_back_stops_at_the_bedroom():
    """
    Asserts that a window moving back by more than the steps left before it
    stops at the bedroom, from which no window starts earlier.
    """
    curriculum = build(back=(2.0, 2.0))
    attempt(curriculum, 0, *[True] * 4)

    assert (
        curriculum.segments[0].latest,
        curriculum.starts.windows[0].earliest
    ) == (0, 0)


def test_an_episode_drawn_before_its_windows_last_move_stays_out_of_its_share():
    """
    Asserts that once a window moves, the starts it gives carry its new
    count of moves, and that an episode drawn before the move leaves its
    share as it stood while one drawn after it counts.
    """
    curriculum = build()
    attempt(curriculum, 0, *[True] * 4)

    shares = []

    for moves in (0, 1):
        curriculum.attempted(
            length    = 10,
            succeeded = True,
            takeover  = taken(curriculum, 0).model_copy(update={"moves": moves})
        )
        shares.append(curriculum.segments[0].recent)

    assert curriculum.starts.windows[0].moves == 1
    assert shares == [[], [True]]


def test_each_move_logs_where_the_window_starts_and_the_share_behind_it(
    logged: list[str]
):
    """
    Asserts that each move of a window logs its segment, the step its window
    now starts by or that it is solved, and the share of its recent episodes
    that succeeded.
    """
    curriculum = build(back=(2.0, 2.0))
    attempt(curriculum, 0, *[True] * 4)
    attempt(curriculum, 0, *[True] * 4)

    assert logged == [
        "Segment 0 starts by step 0 after 100% of its last 4 episodes succeeded",
        "Segment 0 is solved after 100% of its last 4 episodes succeeded"
    ]


def test_each_window_starts_at_its_segments_end_spanning_the_window_steps():
    """
    Asserts that each segment's first window runs the 25 steps up to the
    step its flag is set at, under the buffer of 500 steps alone.
    """
    assert build().starts == Starts(
        limit   = 500,
        windows = [
            Window(earliest=15, latest=40, segment=0),
            Window(earliest=65, latest=90, segment=1)
        ]
    )


def test_the_limit_follows_the_moving_average_of_successful_lengths():
    """
    Asserts that the moving average starts at the first successful length,
    gives each later one the smoothing weight of 0.9, and leaves out each
    failed episode, the limit being twice it plus the buffer.
    """
    curriculum = build()

    for length, succeeded in ((20, True), (900, False), (30, True)):
        curriculum.attempted(
            length    = length,
            succeeded = succeeded,
            takeover  = taken(curriculum, 0)
        )

    assert (curriculum.average, curriculum.limit) == (approx(29), 558)
