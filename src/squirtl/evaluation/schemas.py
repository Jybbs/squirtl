"""
Defines the records an evaluation reads and writes:

- `EvaluationSettings`, every setting an evaluation reads
- `Evaluation`, the episodes one evaluation played of one policy, and the
  measures a reader judges that policy by
"""

from functools  import cached_property
from pydantic   import Field, PositiveInt, model_validator
from statistics import fmean
from typing     import Annotated, Self

from squirtl.emulator.schemas    import Record, UnitInterval, processors
from squirtl.environment.schemas import Outcome
from squirtl.reward.schemas      import Flag, Term


class Evaluation(Record):
    """
    The episodes one evaluation played of one policy, the agent's at a step
    of its run or the random baseline's, from which `measures` derives what
    a reader judges the policy by, and for PPO the same episodes played at
    the policy's most likely action.
    """

    argmax: list[Outcome] | None
    """
    What each episode reached under the same reset seeds where PPO took its
    most likely action at every step, in the order of `outcomes`, or `None`
    for the deep Q-network, PQN, and the random baseline.
    """

    goal: Flag
    """
    The flag whose first setting ended each episode the evaluation counts
    as reaching its goal.
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

    @property
    def greedy(self) -> Self | None:
        """
        Reads the evaluation of the episodes `argmax` holds, at the same
        step and toward the same goal, or `None` where it holds none.
        """
        return None if self.argmax is None else type(self)(
            argmax   = None,
            goal     = self.goal,
            outcomes = self.argmax,
            step     = self.step
        )

    @cached_property
    def measures(self) -> dict[str, float | None]:
        """
        Averages over the episodes the share reaching the goal, the steps
        the episodes reaching it took, the positions reached, the return,
        and each term's part of it, in that order under the name a report
        gives each.

        Returns:
            Each measure under its name, the steps `None` where no episode
            reached the goal.
        """
        lengths = [outcome.length for outcome in self.outcomes if outcome.terminated]

        return {
            "Reached the goal"  : self.reached,
            "Steps to the goal" : fmean(lengths) if lengths else None,
            "Positions"         : fmean(
                outcome.positions for outcome in self.outcomes
            ),
            "Return"            : self.reward,
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
        Averages over the episodes whether each reached the goal, the share
        reaching it.
        """
        return fmean(outcome.terminated for outcome in self.outcomes)

    @property
    def reward(self) -> float:
        """
        Averages the episodes' returns.
        """
        return fmean(outcome.reward for outcome in self.outcomes)

    @model_validator(mode="after")
    def pairs_its_episodes(self) -> Self:
        """
        Refuses an `argmax` holding another count of episodes than
        `outcomes`, since it plays the same episodes again.

        Raises:
            ValueError: Where the counts differ, which Pydantic raises as a
                        `ValidationError`.
        """
        if self.argmax is not None and len(self.argmax) != len(self.outcomes):
            raise ValueError(
                "the episodes at the most likely action and the sampled ones "
                f"number {len(self.argmax):,} and {len(self.outcomes):,}"
            )

        return self


class EvaluationSettings(Record):
    """
    The settings an evaluation reads, each a field of
    `RunSettings.evaluation` and a key under `[tool.squirtl.evaluation]`
    in `pyproject.toml`.
    """

    environments: PositiveInt = Field(default_factory=processors)
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
    The chance of a random action at each step of an evaluation episode of
    the deep Q-network or of PQN, whose default follows Mnih et al. PPO
    samples each action from its policy and plays the same episodes again
    taking its most likely action at every step.
    """
