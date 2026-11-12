"""
Defines `Report`, the figures `squirtl evaluate` prints for the runs it
evaluates, as Markdown a reader pastes into an issue or a pull request, and
`Estimate`, a statistic over runs beside its interval and the count of runs
behind it.
"""

from collections.abc import Callable, Iterable
from numpy           import array, ndarray
from numpy.random    import Generator
from scipy.stats     import bootstrap, mannwhitneyu, trim_mean
from typing          import Self

from squirtl.emulator.schemas   import Record
from squirtl.evaluation.schemas import Evaluation
from squirtl.markdown.tables    import tabulate

type Pairs = dict[str, tuple[Evaluation, Evaluation]]


class Estimate(Record):
    """
    A statistic over runs beside its 95% percentile bootstrap interval,
    which SciPy's `bootstrap` gives where every sample holds two runs or
    more, and the count of runs in each sample it reads.
    """

    interval: tuple[float, float] | None
    """
    The bounds of the 95% percentile bootstrap interval, or `None` where a
    sample holds a single run.
    """

    runs: tuple[int, ...]
    """
    The count of runs in each sample.
    """

    value: float
    """
    The statistic over the samples as they stand.
    """

    def __str__(self) -> str:
        """
        Spells the value, its interval in brackets, and the runs behind it.
        """
        bounds = "" if self.interval is None else " [{:,.5g}, {:,.5g}]".format(
            *self.interval
        )
        counts = " and ".join(map(str, self.runs))
        noun   = "run" if self.runs == (1,) else "runs"

        return f"{self.value:,.5g}{bounds} over {counts} {noun}"

    @property
    def share(self) -> str:
        """
        Spells the value as a share of evaluation episodes, in whole points
        beside its interval where the share is neither every episode nor
        none.
        """
        match self.value:
            case 1 : return "in every evaluation episode"
            case 0 : return "in no evaluation episode"

        bounds = "" if self.interval is None else " [{:.0f}, {:.0f}]".format(
            *(100 * bound for bound in self.interval)
        )

        return f"in {self.value:.0%}{bounds}"

    @classmethod
    def improvement(cls, first: ndarray, second: ndarray, *, generator: Generator) -> Self:
        """
        Estimates the probability that a run of one agent scores above a
        run of another, from `first` and `second`, each holding one score
        per run. The estimate is the Mann-Whitney statistic of `first` over
        the count of pairs of runs, a tie counting half, as Agarwal et al.
        compare two agents.
        """
        return cls.resampled(
            lambda first, second, axis: mannwhitneyu(first, second, axis=axis).statistic
            / (first.shape[axis] * second.shape[axis]),
            first,
            second,
            generator = generator
        )

    @classmethod
    def interquartile(cls, values: ndarray, *, generator: Generator) -> Self:
        """
        Estimates the interquartile mean of `values`, one per run, the mean
        of the runs left once `trim_mean` cuts `int(0.25 * len(values))`
        from each end, every run where there are fewer than four, as Agarwal
        et al. aggregate runs.
        """
        return cls.resampled(
            lambda values, axis: trim_mean(values, 0.25, axis=axis),
            values,
            generator = generator
        )

    @classmethod
    def resampled(
        cls,
        statistic : Callable[..., float | ndarray],
        *samples  : ndarray,
        generator : Generator
    ) -> Self:
        """
        Computes `statistic` over `samples`, and its 95% percentile interval
        over resamples `generator` draws of each sample apart from the
        others, since the default `BCa` interval yields no value where every
        run scores the same.
        """
        runs = tuple(map(len, samples))

        return cls(
            interval = None if min(runs) < 2 else tuple(
                bootstrap(samples, statistic, method="percentile", rng=generator)
                    .confidence_interval
            ),
            runs  = runs,
            value = statistic(*samples, axis=-1)
        )


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
        agent's or the `--against` run's followed by its baseline's, each
        naming the goal its episodes ended at.
        """
        return tabulate(
            header = ["Run", "Policy", "Goal", "Step", "Episodes", *self.measures],
            rows   = (
                [
                    f"`{name}`",
                    policy,
                    f"`{evaluation.goal.name}`",
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
        across  = tabulate(
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
