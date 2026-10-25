"""
Defines `Report`, the figures `squirtl evaluate` prints for the runs it
evaluates, as Markdown a reader pastes into an issue or a pull request.
"""

from collections.abc import Collection, Iterable
from numpy           import array
from numpy.random    import Generator

from squirtl.emulator.schemas   import Record
from squirtl.evaluation.schemas import Estimate, Evaluation

type Pairs = dict[str, tuple[Evaluation, Evaluation]]


class Report(Record):
    """
    The last evaluation of each run `squirtl evaluate` names, beside the
    random baseline's under the same seeds, and the Markdown it prints from
    them.
    """

    against: Pairs
    """
    The agent's evaluation and the baseline's for each run `--against`
    names, under its name, empty where the command names none.
    """

    runs: Pairs
    """
    The agent's evaluation and the baseline's for each run the command
    names, under its name.
    """

    @property
    def columns(self) -> dict[str, list[Evaluation]]:
        """
        Gathers the evaluations behind each column of the table across the
        runs, the agent's and the baseline's of each run the command names,
        then the agent's of each run `--against` names where there are any.
        """
        return {
            "Agent"    : [agent for agent, _ in self.runs.values()],
            "Baseline" : [baseline for _, baseline in self.runs.values()]
        } | ({
            "Against": [agent for agent, _ in self.against.values()]
        } if self.against else {})

    @property
    def listing(self) -> str:
        """
        Lays out a table holding a row of measures for each evaluation, the
        agent's or the `--against` run's followed by its baseline's.
        """
        return table(
            header = ["Run", "Policy", "Step", "Episodes", *self.measures],
            rows   = (
                [
                    f"`{name}`",
                    policy,
                    "" if evaluation.step is None else f"{evaluation.step:,}",
                    str(len(evaluation.outcomes)),
                    *map(figure, evaluation.measures.values())
                ]
                for label, group in (("Agent", self.runs), ("Against", self.against))
                for name, pair in group.items()
                for policy, evaluation in zip((label, "Baseline"), pair)
            )
        )

    @property
    def measures(self) -> list[str]:
        """
        Names each measure in the order an evaluation derives them.
        """
        return list(self.columns["Agent"][0].measures)

    @staticmethod
    def improvement(
        first     : Iterable[Evaluation],
        second    : Iterable[Evaluation],
        *,
        generator : Generator
    ) -> Estimate:
        """
        Estimates the probability that a run whose evaluation `first` holds
        beats a run whose evaluation `second` holds, on mean return.
        """
        return Estimate.improvement(
            *(
                array([evaluation.reward for evaluation in evaluations])
                for evaluations in (first, second)
            ),
            generator = generator
        )

    @staticmethod
    def interquartile(
        evaluations : Iterable[Evaluation],
        measure     : str,
        *,
        generator   : Generator
    ) -> str:
        """
        Spells the interquartile mean of `measure` across `evaluations`,
        leaving out each run where it is `None`, or `none` where it is
        `None` for every run.
        """
        values = [
            value
            for evaluation in evaluations
            if (value := evaluation.measures[measure]) is not None
        ]

        return str(
            Estimate.interquartile(array(values), generator=generator)
        ) if values else "none"

    def markdown(self, generator: Generator) -> str:
        """
        Lays the report out as `listing`, a table of each measure's
        interquartile mean across the runs of each column, and a sentence
        for each probability of improvement on the runs' mean returns, each
        interval over the resamples `generator` draws.
        """
        columns = self.columns
        across  = table(
            header = ["Measure", *columns],
            rows   = (
                [
                    measure,
                    *(
                        self.interquartile(evaluations, measure, generator=generator)
                        for evaluations in columns.values()
                    )
                ]
                for measure in self.measures
            )
        )
        comparisons = [
            f"The agent beats {rival} with a probability of "
            f"{self.improvement(columns['Agent'], columns[key], generator=generator)}, "
            f"on each run's mean return."
            for key, rival in (
                ("Baseline", "its baseline"),
                ("Against", "the runs against it")
            )
            if key in columns
        ]

        return "\n\n".join([self.listing, across, *comparisons])


def figure(value: float | None) -> str:
    """
    Spells a measure to five significant digits, or `none` where it is
    `None`.
    """
    return "none" if value is None else f"{value:,.5g}"


def table(header: Collection[str], rows: Iterable[Iterable[str]]) -> str:
    """
    Lays `rows` out as a Markdown table beneath `header`, bolding each
    header cell.
    """
    return "\n".join(
        f"| {' | '.join(row)} |"
        for row in ([f"**{cell}**" for cell in header], ["---"] * len(header), *rows)
    )
