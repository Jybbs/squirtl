"""
Pins the Markdown `Report` lays out, covering:

- Each run's measures, each measure's interquartile mean across the runs
  beside the baseline's and the `--against` runs', and each probability of
  improvement, under a seeded generator
- A report naming no `--against` run, which leaves out its column and its
  sentence
- A measure no run reaches, which spells `none`
"""

from common.evaluation import outcome, played
from numpy.random      import default_rng
from syrupy.assertion  import SnapshotAssertion

from squirtl.evaluation.report  import Report
from squirtl.evaluation.schemas import Evaluation
from squirtl.reward.schemas     import Term


def test_a_report_lays_out_each_run_each_measure_and_each_comparison(
    snapshot: SnapshotAssertion
):
    """
    Asserts that a report of three runs against two prints the table of each
    run's measures, the table of each measure's interquartile mean with its
    interval and runs, and both probabilities of improvement its fixture
    file holds, one run reaching the starter in 40 steps.
    """
    reached = outcome(
        length = 40,
        reward = 0.6025,
        shares = dict.fromkeys(Term, 0.0) | {Term.NOVELTY: 0.0025, Term.STARTER: 0.6},
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
                Evaluation(outcomes=[reached, outcome()], step=100),
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
    measure no run reaches, the steps to the starter here, spells `none`.
    """
    markdown = Report(
        against = {},
        runs    = {"20261003T000000.000000Z": (played([0.5], 100), played([0.0], None))}
    ).markdown(default_rng(0))

    assert ("Against" in markdown, "against it" in markdown) == (False, False)
    assert "| Steps to the starter | none | none |" in markdown
