"""
Defines what the tests of an evaluation build from:

- `outcome` and `played`, which build what one episode reached and the
  evaluation of several such episodes
- `EvaluatorStandIn`, which stands in for `Evaluator`, answering each
  evaluation a run asks of it without starting a worker process
"""

from collections.abc import Iterable
from contextlib      import AbstractContextManager

from squirtl.agent.checkpoint    import Weights
from squirtl.environment.schemas import Outcome
from squirtl.evaluation.schemas  import Evaluation
from squirtl.reward.schemas      import Term


class EvaluatorStandIn(AbstractContextManager):
    """
    Stands in for `Evaluator`, holding the arguments it was built with and
    the step of each evaluation asked of it, `None` for the baseline's,
    in the order asked. It answers each with one episode `played` builds,
    the agent's reaching the starter for a return of the step over 1,000,
    whereas the baseline's is truncated at a return of 0.125.
    """

    def __exit__(self, *raised: object):
        """
        Leaves the `with` block, holding no process to close.
        """

    def __init__(self, *arguments: object):
        """
        Records the arguments `Benchmark.from_run` builds an `Evaluator`
        with.
        """
        self.arguments = arguments
        self.asked     = []

    def baseline(self) -> Evaluation:
        """
        Records the baseline's evaluation and answers it.
        """
        self.asked.append(None)

        return played([0.125], None)

    def evaluate(self, weights: Weights) -> Evaluation:
        """
        Records the agent's evaluation at the step of `weights` and answers
        it.
        """
        self.asked.append(weights.step)

        return played([weights.step / 1000], weights.step, terminated=True)


def outcome(reward: float = 0.0025, **fields: object) -> Outcome:
    """
    Builds the outcome of a truncated episode of 100 steps reaching 10
    positions for a return of `reward`, all of it the novelty, unless a
    keyword sets another field.
    """
    return Outcome(
        **{
            "length"     : 100,
            "positions"  : 10,
            "reward"     : reward,
            "seconds"    : 1.0,
            "shares"     : dict.fromkeys(Term, 0.0) | {Term.NOVELTY: reward},
            "terminated" : False
        }
        | fields
    )


def played(rewards: Iterable[float], step: int | None, **fields: object) -> Evaluation:
    """
    Builds the evaluation at `step` of one truncated episode per return in
    `rewards`, all of it the novelty, unless a keyword sets another field of
    each episode.
    """
    return Evaluation(
        outcomes = [outcome(reward, **fields) for reward in rewards],
        step     = step
    )
