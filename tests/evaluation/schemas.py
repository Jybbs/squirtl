"""
Pins the records an evaluation reads and writes, covering:

- The measures an evaluation derives from its episodes, the steps to the
  goal among them, which no episode reaching it leaves out
- The environments an evaluation runs by default, and an evaluation holding
  no episode, which is refused
"""

from common.evaluation import outcome, played
from pydantic          import ValidationError
from pytest            import MonkeyPatch, approx, raises

from squirtl.evaluation.schemas import Evaluation, EvaluationSettings
from squirtl.reward.schemas     import Event, Term


def test_an_evaluation_averages_each_measure_over_its_episodes():
    """
    Asserts that two episodes, one reaching the goal in 40 steps and one
    truncated after 100, average to half reaching it, 40 steps to it, the
    mean of their positions and returns, and each term's mean pay.
    """
    evaluation = Evaluation(
        goal     = Event.EVENT_GOT_STARTER,
        outcomes = [
            outcome(
                length     = 40,
                positions  = 30,
                reward     = 0.905,
                shares     = {Term.GOAL: 0.6, Term.MILESTONE: 0.3, Term.NOVELTY: 0.005},
                terminated = True
            ),
            outcome()
        ],
        step = 7
    )

    assert evaluation.measures == {
        "Goal pay"          : 0.3,
        "Milestone pay"     : 0.15,
        "Novelty pay"       : approx(0.00375),
        "Positions"         : 20.0,
        "Reached the goal"  : 0.5,
        "Return"            : approx(0.45375),
        "Steps to the goal" : 40.0
    }


def test_an_evaluation_no_episode_of_which_reaches_the_goal_takes_no_steps_to_it():
    """
    Asserts that an evaluation none of whose episodes reaches the goal
    reports none reaching it and no steps to it, rather than a mean over
    no episodes.
    """
    measures = played([0.0, 0.0], 100).measures

    assert (measures["Reached the goal"], measures["Steps to the goal"]) == (
        0.0, None
    )


def test_an_evaluation_refuses_an_empty_list_of_episodes():
    """
    Asserts that an evaluation holding no episode is refused, since each of
    its measures averages over its episodes.
    """
    with raises(ValidationError, match="at least 1 item"):
        Evaluation(goal=Event.EVENT_GOT_STARTER, outcomes=[], step=None)


def test_an_evaluation_runs_one_environment_where_the_cpus_are_unknown(
    monkeypatch: MonkeyPatch
):
    """
    Asserts that an evaluation runs one environment by default where
    `process_cpu_count` cannot tell how many CPUs the process may use.
    """
    monkeypatch.setattr("squirtl.emulator.schemas.process_cpu_count", lambda: None)

    assert EvaluationSettings().environments == 1
