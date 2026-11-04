"""
Defines the records an evaluation reads and writes:

- `EvaluationSettings`, every setting an evaluation reads
- `Evaluation`, the episodes one evaluation played of one policy, and the
  measures a reader judges that policy by
"""

from functools  import cached_property
from os         import process_cpu_count
from pydantic   import Field, PositiveInt
from statistics import fmean
from typing     import Annotated

from squirtl.emulator.schemas    import Record, UnitInterval
from squirtl.environment.schemas import Outcome
from squirtl.reward.schemas      import Term


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
