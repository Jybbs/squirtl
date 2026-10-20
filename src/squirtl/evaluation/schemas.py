"""
Defines the records an evaluation reads and writes:

- `EvaluationSettings`, every setting an evaluation reads
- `Evaluation`, the episodes one evaluation played of one policy, and the
  measures a reader judges that policy by
- `Estimate`, a statistic over runs beside its interval and the count of
  runs behind it
"""

from collections.abc import Callable
from functools       import cached_property
from numpy           import ndarray
from numpy.random    import Generator
from os              import process_cpu_count
from pydantic        import Field, PositiveInt
from scipy.stats     import bootstrap, mannwhitneyu, trim_mean
from statistics      import fmean
from typing          import Annotated, Self

from squirtl.emulator.schemas    import Record, UnitInterval
from squirtl.environment.schemas import Outcome
from squirtl.reward.schemas      import Term


class Estimate(Record):
    """
    A statistic over runs beside its 95% percentile bootstrap interval,
    which scipy's `bootstrap` gives where every sample holds two runs or
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
        of the middle half once `trim_mean` cuts a quarter of the runs from
        each end, as Agarwal et al. aggregate runs.
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


class Evaluation(Record):
    """
    The episodes one evaluation played of one policy, the agent's at a step
    of its run or the random baseline's, from which `measures` derives what
    a reader judges the policy by.
    """

    outcomes: Annotated[list[Outcome], Field(min_length=1)]
    """
    What each episode reached, in the order of the seeds they started from.
    """

    step: int | None
    """
    The steps the agent had taken when the evaluation read it, or `None` for
    the random baseline.
    """

    @cached_property
    def measures(self) -> dict[str, float | None]:
        """
        Averages over the episodes the share reaching the starter, the steps
        the episodes reaching it took, the positions reached, the return,
        and each term's part of it, in that order under the name a report
        gives each.

        Returns:
            Each measure under its name, the steps `None` where no episode
            reached the starter.
        """
        lengths = [outcome.length for outcome in self.outcomes if outcome.terminated]

        return {
            "Reached the starter"  : self.reached,
            "Steps to the starter" : fmean(lengths) if lengths else None,
            "Positions"            : fmean(
                outcome.positions for outcome in self.outcomes
            ),
            "Return"               : self.reward,
            **{
                f"{term.capitalize()} pay": fmean(
                    outcome.shares[term] for outcome in self.outcomes
                )
                for term in Term
            }
        }

    @property
    def reached(self) -> float:
        """
        Averages over the episodes whether each reached the starter, the
        share reaching it.
        """
        return fmean(outcome.terminated for outcome in self.outcomes)

    @property
    def reward(self) -> float:
        """
        Averages the episodes' returns.
        """
        return fmean(outcome.reward for outcome in self.outcomes)


class EvaluationSettings(Record):
    """
    The settings an evaluation reads, each a field of
    `RunSettings.evaluation` and a key under `[tool.squirtl.evaluation]`
    in `pyproject.toml`.
    """

    environments: PositiveInt = Field(default_factory=lambda: process_cpu_count() or 1)
    """
    The environments an evaluation plays its episodes across in parallel,
    each in a worker process of its own, which defaults to the CPUs the
    process may use.
    """

    episodes: PositiveInt = 30
    """
    The episodes each evaluation plays of the agent and of the random
    baseline, whose default follows Mnih et al.
    """

    epsilon: UnitInterval = 0.05
    """
    The chance of a random action at each step of the agent's evaluation
    episodes, whose default follows Mnih et al.
    """
