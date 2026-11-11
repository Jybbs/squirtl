"""
Pins the records an evaluation reads and writes, covering:

- The measures an evaluation derives from its episodes, the steps to the
  goal among them, which no episode reaching it leaves out
- The environments an evaluation runs by default, and an evaluation holding
  no episode, which is refused
- The episodes PPO played at its most likely action, which a line must name
  and which read as an evaluation of their own
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
        argmax   = None,
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


def test_an_evaluation_line_written_without_the_argmax_episodes_is_refused():
    """
    Asserts that a line holding no `argmax` field, as a line written before
    the field holds, is refused naming it rather than read as a sampled
    result.
    """
    line = played([0.5], 100).model_dump_json(exclude={"argmax"})

    with raises(ValidationError, match=r"argmax\n  Field required"):
        Evaluation.model_validate_json(line)


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
        Evaluation(
            argmax   = None,
            goal     = Event.EVENT_GOT_STARTER,
            outcomes = [],
            step     = None
        )


def test_an_evaluation_runs_one_environment_where_the_cpus_are_unknown(
    monkeypatch: MonkeyPatch
):
    """
    Asserts that an evaluation runs one environment by default where
    `process_cpu_count` cannot tell how many CPUs the process may use.
    """
    monkeypatch.setattr("squirtl.evaluation.schemas.process_cpu_count", lambda: None)

    assert EvaluationSettings().environments == 1


def test_the_argmax_episodes_read_as_an_evaluation_of_their_own():
    """
    Asserts that `greedy` reads the episodes `argmax` holds at the same step
    and goal, measured apart from the sampled episodes, and reads `None`
    where the evaluation holds none.
    """
    sampled = played([0.0, 0.0], 100, goal=Event.EVENT_GOT_POKEDEX)
    argmax  = played([0.5], 100, terminated=True).outcomes

    greedy = sampled.model_copy(update={"argmax": argmax}).greedy

    assert (greedy.goal, greedy.outcomes, greedy.step, greedy.argmax) == (
        Event.EVENT_GOT_POKEDEX, argmax, 100, None
    )
    assert (greedy.reached, sampled.reached, sampled.greedy) == (1.0, 0.0, None)
