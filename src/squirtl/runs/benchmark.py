"""
Defines `Benchmark`, the agent's evaluation at one step of a run beside the
random baseline's, which `Trainer` reads at each evaluation interval and
`squirtl evaluate` at each run's last checkpoint.
"""

from typing import Self

from squirtl.agent.checkpoint      import Weights
from squirtl.emulator.schemas      import Cartridge, Record
from squirtl.environment.overworld import Overworld
from squirtl.evaluation.evaluator  import Evaluator
from squirtl.evaluation.schemas    import Evaluation
from squirtl.runs.schemas          import Run
from squirtl.runs.settings         import Stream


class Benchmark(Record):
    """
    The agent's evaluation at one step of a run beside the random baseline's
    under the same seeds, each of which the run holds once it is played.
    """

    agent: Evaluation
    """
    The agent's evaluation, played from the network whose weights `from_run`
    takes.
    """

    baseline: Evaluation
    """
    The random baseline's evaluation, under the seeds the agent's evaluation
    starts from.
    """

    @classmethod
    def from_run(cls, cartridge: Cartridge, run: Run, weights: Weights) -> Self:
        """
        Reads the agent's evaluation at the step of `weights` and the random
        baseline's from `run`, playing whichever of the two it lacks on
        `cartridge` under the evaluation settings and the evaluation stream
        the run recorded and writing it there.

        Raises:
            ValueError: Where it plays either and the intro on `cartridge`
                        leaves the console in a state of another digest than
                        the one `run` recorded, before any episode.
        """
        agent = next(
            (
                evaluation
                for evaluation in run.evaluated
                if evaluation.step == weights.step
            ),
            None
        )
        baseline = run.baselined

        if agent is None or baseline is None:
            settings = run.settings

            with Evaluator(
                settings.agent.algorithm,
                settings.agent.device,
                settings.seeds[Stream.EVALUATION],
                settings.evaluation,
                Overworld.specification(
                    cartridge,
                    settings.emulator,
                    settings.environment,
                    settings.reward
                )
            ) as evaluator:
                run.check(evaluator.digest)

                if agent is None:
                    agent = evaluator.evaluate(weights)
                    run.append(run.evaluations, agent)

                if baseline is None:
                    baseline = evaluator.baseline()
                    run.baseline.write_text(
                        baseline.model_dump_json(),
                        encoding = "utf-8"
                    )

        return cls(agent=agent, baseline=baseline)
