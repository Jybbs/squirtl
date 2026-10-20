"""
Pins the records an evaluation reads and writes, covering:

- The measures an evaluation derives from its episodes, the steps to the
  starter among them, which no episode reaching it leaves out
- The interquartile mean and the probability of improvement, each beside
  its percentile interval, which one run leaves out and runs scoring the
  same close onto their score, and how each spells itself
- The environments an evaluation runs by default, and an evaluation holding
  no episode, which is refused
"""

from common.evaluation import outcome, played
from numpy             import array
from numpy.random      import default_rng
from pydantic          import ValidationError
from pytest            import MonkeyPatch, approx, mark, param, raises

from squirtl.evaluation.schemas import Estimate, Evaluation, EvaluationSettings
from squirtl.reward.schemas     import Term


def test_an_evaluation_averages_each_measure_over_its_episodes():
    """
    Asserts that two episodes, one reaching the starter in 40 steps and one
    truncated after 100, average to half reaching it, 40 steps to it, the
    mean of their positions and returns, and each term's mean pay.
    """
    shares     = {Term.MILESTONE: 0.3, Term.NOVELTY: 0.005, Term.STARTER: 0.6}
    evaluation = Evaluation(
        outcomes = [
            outcome(
                length     = 40,
                positions  = 30,
                reward     = 0.905,
                shares     = shares,
                terminated = True
            ),
            outcome()
        ],
        step = 7
    )

    assert evaluation.measures == {
        "Milestone pay"        : 0.15,
        "Positions"            : 20.0,
        "Reached the starter"  : 0.5,
        "Return"               : approx(0.45375),
        "Starter pay"          : 0.3,
        "Novelty pay"          : approx(0.00375),
        "Steps to the starter" : 40.0
    }


def test_an_evaluation_no_episode_of_which_reaches_the_starter_takes_no_steps_to_it():
    """
    Asserts that an evaluation none of whose episodes reaches the starter
    reports none reaching it and no steps to it, rather than a mean over
    no episodes.
    """
    measures = played([0.0, 0.0], 100).measures

    assert (measures["Reached the starter"], measures["Steps to the starter"]) == (
        0.0, None
    )


def test_an_evaluation_refuses_an_empty_list_of_episodes():
    """
    Asserts that an evaluation holding no episode is refused, since each of
    its measures averages over its episodes.
    """
    with raises(ValidationError, match="at least 1 item"):
        Evaluation(outcomes=[], step=None)


def test_an_evaluation_runs_one_environment_where_the_cpus_are_unknown(
    monkeypatch: MonkeyPatch
):
    """
    Asserts that an evaluation runs one environment by default where
    `process_cpu_count` cannot tell how many CPUs the process may use.
    """
    monkeypatch.setattr("squirtl.evaluation.schemas.process_cpu_count", lambda: None)

    assert EvaluationSettings().environments == 1


@mark.parametrize(
    ("values", "interval"),
    [
        param([0.25],       None,         id="one-run"),
        param([0.25, 0.25], (0.25, 0.25), id="runs-scoring-the-same")
    ]
)
def test_an_interval_leaves_out_one_run_and_closes_onto_runs_scoring_the_same(
    interval : tuple[float, float] | None,
    values   : list[float]
):
    """
    Asserts that one run carries no interval, since scipy's `bootstrap`
    resamples two runs or more, whereas runs scoring the same carry the
    interval closing onto their score, where `BCa` would yield none.
    """
    assert Estimate.interquartile(array(values), generator=default_rng(0)).interval == (
        interval
    )


def test_the_interquartile_mean_cuts_a_quarter_of_the_runs_from_each_end():
    """
    Asserts that the interquartile mean of five runs averages the middle
    three once `trim_mean` cuts one from each end, leaving out the run at
    100, and that its interval spans that mean.
    """
    estimate = Estimate.interquartile(
        array([0.0, 1.0, 2.0, 3.0, 100.0]),
        generator = default_rng(0)
    )
    low, high = estimate.interval

    assert (estimate.value, estimate.runs, low <= 2.0 <= high) == (2.0, (5,), True)


@mark.parametrize(
    ("estimate", "spelled"),
    [
        param(
            Estimate(interval=(0.125, 0.375), runs=(5,), value=0.25),
            "0.25 [0.125, 0.375] over 5 runs",
            id = "an-interval"
        ),
        param(
            Estimate(interval=None, runs=(1,), value=4812.0),
            "4,812 over 1 run",
            id = "one-run"
        ),
        param(
            Estimate(interval=(0.5, 1.0), runs=(5, 4), value=0.75),
            "0.75 [0.5, 1] over 5 and 4 runs",
            id = "two-samples"
        )
    ]
)
def test_an_estimate_spells_its_value_its_interval_and_its_runs(
    estimate : Estimate,
    spelled  : str
):
    """
    Asserts that an estimate spells its value to five significant digits,
    its interval in brackets where it has one, and the count of runs behind
    each sample it reads.
    """
    assert str(estimate) == spelled


def test_the_probability_of_improvement_counts_a_tie_half():
    """
    Asserts that runs scoring 1, 2, and 3 beat runs scoring 0, 2, and 0 in
    seven of the nine pairs and tie in one, for a probability of 7.5 over 9.
    """
    estimate = Estimate.improvement(
        array([1.0, 2.0, 3.0]),
        array([0.0, 2.0, 0.0]),
        generator = default_rng(0)
    )

    assert (estimate.value, estimate.runs) == (approx(7.5 / 9), (3, 3))
