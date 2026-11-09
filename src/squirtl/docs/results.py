"""
Defines `Results`, the measured runs the site's Results section draws, read
from the run directories committed under `docs/runs/`, which `squirtl write
docs` writes into the site as JSON, beside `Trained`, one of those runs, and
`Comparison`, the runs of one agent set against their baselines.
"""

from collections.abc import Iterable
from itertools       import groupby
from numpy           import array
from numpy.random    import default_rng
from operator        import attrgetter
from pathlib         import Path
from typing          import ClassVar, Self

from squirtl.agent.schemas      import Algorithm
from squirtl.emulator.schemas   import EmulatorSettings, Record
from squirtl.evaluation.report  import Estimate
from squirtl.evaluation.schemas import Evaluation
from squirtl.runs.schemas       import Run


class Score(Record):
    """
    What one evaluation measured, the share of its episodes reaching the
    starter and their mean return, at the step of the run it read.
    """

    reached: float
    """
    The share of the episodes reaching the starter.
    """

    reward: float
    """
    The episodes' mean return.
    """

    step: int | None
    """
    The steps the agent had taken, or `None` for the random baseline.
    """

    @classmethod
    def of(cls, evaluation: Evaluation) -> Self:
        """
        Reads the score of `evaluation`.
        """
        return cls.model_validate(evaluation, from_attributes=True)


class Trained(Record):
    """
    One run the Results section draws, the agent's score at each of its
    evaluations beside the random baseline's under the same seeds.
    """

    agent: Algorithm
    """
    The agent the run trained.
    """

    baseline: Score
    """
    The random baseline's score under the run's evaluation seeds.
    """

    curriculum: bool
    """
    Whether the run started its training episodes along a demonstration.
    """

    name: str
    """
    The run's name, the folder under `docs/runs/` holding it.
    """

    scores: tuple[Score, ...]
    """
    The agent's score at each evaluation, in the order the run played them.
    """

    seed: int
    """
    The seed the run's random draws derive from.
    """

    @property
    def last(self) -> Score:
        """
        Picks the agent's score at the run's last evaluation.
        """
        return self.scores[-1]

    @classmethod
    def read(cls, directory: Path) -> Self:
        """
        Reads the run `directory` holds.

        Raises:
            ValueError: Where the run read a cartridge other than the
                        default path, which would carry a local path into
                        the checkout, or holds no evaluation of the agent or
                        of the random baseline.
        """
        run = Run.read(directory)

        if run.settings.emulator.cartridge != EmulatorSettings().cartridge:
            raise ValueError(
                f"{directory} read the cartridge {run.settings.emulator.cartridge}"
            )

        if not (scores := tuple(map(Score.of, run.evaluated))):
            raise ValueError(f"{directory} holds no evaluation")

        if (baseline := run.baselined) is None:
            raise ValueError(f"{directory} holds no baseline")

        return cls(
            agent      = run.settings.agent.algorithm,
            baseline   = Score.of(baseline),
            curriculum = run.settings.curriculum.demonstration is not None,
            name       = run.name,
            scores     = scores,
            seed       = run.settings.seed
        )


class Comparison(Record):
    """
    The runs of one agent, trained with or without the curriculum, set
    against the random baseline under the same seeds at each run's last
    evaluation.
    """

    agent: Algorithm
    """
    The agent the runs trained.
    """

    baseline: Estimate
    """
    The interquartile mean across the runs of the baseline's share reaching
    the starter.
    """

    beats: Estimate
    """
    The probability that a run of the agent beats a run of the baseline on
    mean return.
    """

    curriculum: bool
    """
    Whether the runs started their training episodes along a demonstration.
    """

    reached: Estimate
    """
    The interquartile mean across the runs of the agent's share reaching
    the starter.
    """

    @classmethod
    def across(cls, runs: Iterable[Trained]) -> Self:
        """
        Compares `runs`, all of one agent and one curriculum, against their
        baselines, each interval over resamples drawn from the runs' seeds.
        """
        runs      = tuple(runs)
        generator = default_rng(sorted(run.seed for run in runs))

        return cls(
            agent    = runs[0].agent,
            baseline = Estimate.interquartile(
                array([run.baseline.reached for run in runs]),
                generator = generator
            ),
            beats = Estimate.improvement(
                array([run.last.reward for run in runs]),
                array([run.baseline.reward for run in runs]),
                generator = generator
            ),
            curriculum = runs[0].curriculum,
            reached    = Estimate.interquartile(
                array([run.last.reached for run in runs]),
                generator = generator
            )
        )


class Results(Record):
    """
    Every run committed under `docs/runs/`, beside the comparison of each
    agent's runs against the random baseline.
    """

    folder: ClassVar[Path] = Path("docs/runs")

    comparisons: tuple[Comparison, ...]
    """
    One comparison for each agent and curriculum the runs train, in the
    order of the agent's name and then without the curriculum before with
    it.
    """

    runs: tuple[Trained, ...]
    """
    Each run, in the order of its name.
    """

    @classmethod
    def read(cls, folder: Path = folder) -> Self:
        """
        Reads every run directory `folder` holds, none where it is missing.
        """
        runs = tuple(
            Trained.read(directory)
            for directory in sorted(folder.iterdir() if folder.is_dir() else ())
        )
        group = attrgetter("agent", "curriculum")

        return cls(
            comparisons = tuple(
                Comparison.across(members)
                for _, members in groupby(sorted(runs, key=group), key=group)
            ),
            runs = runs
        )
