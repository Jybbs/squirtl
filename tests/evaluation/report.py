"""
Pins the Markdown `Report` lays out, covering:

- Each run's measures, each measure's interquartile mean across the runs
  beside the baseline's and the `--against` runs', and each probability of
  improvement, under a seeded generator
- A report naming no `--against` run, which leaves out its column and its
  sentence
- A measure no run reaches, which spells `none`
- The interquartile mean and the probability of improvement, each beside
  its percentile interval, which one run leaves out and runs scoring the
  same close onto their score, and how each spells itself
"""

from common.evaluation import outcome, played
from numpy             import array
from numpy.random      import default_rng
from pytest            import approx, mark, param
from syrupy.assertion  import SnapshotAssertion

from squirtl.evaluation.report import Estimate, Report
from squirtl.reward.schemas    import Term


def test_a_report_lays_out_each_run_each_measure_and_each_comparison(
    snapshot: SnapshotAssertion
):
    """
    Asserts that a report of three runs against two prints the table of each
    run's measures, the table of each measure's interquartile mean with its
    interval and runs, and both probabilities of improvement its fixture
    file holds, one run reaching its goal in 40 steps.
    """
    reached = outcome(
        length     = 40,
        reward     = 0.6025,
        shares     = dict.fromkeys(Term, 0.0) | {Term.GOAL: 0.6, Term.NOVELTY: 0.0025},
        terminated = True
    )
    report = Report(
        against = {
            "20261006T000000.000000Z": (
                played([0.0, 0.25], 100),
                played([0.0, 0.0], None)
            ),

            "20261007T000000.000000Z": (
                played([0.5, 0.25], 100),
                played([0.0, 0.25], None)
            )
        },
        runs = {
            "20261003T000000.000000Z": (
                played([0.0], 100).model_copy(
                    update = {"outcomes": [reached, outcome()]}
                ),
                played([0.0, 0.0], None)
            ),

            "20261004T000000.000000Z": (
                played([0.5, 0.5], 1_000_000),
                played([0.0, 0.25], None)
            ),

            "20261005T000000.000000Z": (
                played([0.75, 0.5], 100),
                played([0.0, 0.0], None)
            )
        }
    )

    assert report.markdown(default_rng(0)) == snapshot


def test_a_report_naming_no_rival_runs_leaves_out_their_column_and_comparison():
    """
    Asserts that a report naming no `--against` run carries no `Against`
    column and no sentence comparing the agent with such runs, and that a
    measure no run reaches, the steps to the goal here, spells `none`.
    """
    markdown = Report(
        against = {},
        runs    = {"20261003T000000.000000Z": (played([0.5], 100), played([0.0], None))}
    ).markdown(default_rng(0))

    assert ("Against" in markdown, "against it" in markdown) == (False, False)
    assert "| Steps to the goal | none | none |" in markdown


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
    Asserts that one run carries no interval, since SciPy's `bootstrap`
    resamples two runs or more, whereas runs scoring the same carry the
    interval closing onto their score, where `BCa` would yield none.
    """
    assert Estimate.interquartile(array(values), generator=default_rng(0)).interval == (
        interval
    )


def test_the_interquartile_mean_of_four_runs_averages_the_middle_two():
    """
    Asserts that the interquartile mean of four runs averages the middle two
    once `trim_mean` cuts a quarter of them from each end, leaving out the
    run at 100, and that its interval spans that mean.
    """
    estimate = Estimate.interquartile(
        array([0.0, 1.0, 2.0, 100.0]),
        generator = default_rng(0)
    )
    low, high = estimate.interval

    assert (estimate.value, estimate.runs, low <= 1.5 <= high) == (1.5, (4,), True)


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
