"""
Defines `Results`, the measured runs the site's Results section draws,
read from the run directories committed under `docs/runs/`, which `squirtl
write docs` writes into the site as JSON, beside `Trained`, one of those
runs, `Comparison`, the runs of one agent set against their baselines, and
`ReleaseSettings`, which names the run among them a release plays.
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
from squirtl.reward.schemas     import Event, Flag
from squirtl.runs.schemas       import Run, RunListing


class ReleaseSettings(Record):
    """
    The settings `squirtl pack` writes a release's runs under, the runs
    committed under `Results.folder`.
    """

    recommended_run: str = "20261111T020527.724383Z"
    """
    The name of the run a release plays where no selection names one.
    """


class Score(Record):
    """
    What one evaluation measured, the share of its episodes reaching the
    run's goal and their mean return, at the step of the run it read.
    """

    reached: float
    """
    The share of the episodes reaching the run's goal.
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


class Trained(RunListing):
    """
    One run the Results section draws, the agent's score at each of its
    evaluations beside the random baseline's under the same seeds, its name
    the folder under `docs/runs/` holding it.
    """

    baseline: Score
    """
    The random baseline's score under the run's evaluation seeds.
    """

    goal: Flag
    """
    The flag whose first setting ended the run's episodes.
    """

    scores: tuple[Score, ...]
    """
    The agent's score at each evaluation, in the order the run played them.
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
                        default path or followed a demonstration at an
                        absolute path, either of which would carry a local
                        path into the checkout, or holds no evaluation of
                        the agent or of the random baseline.
        """
        run = Run.read(directory)

        if run.settings.emulator.cartridge != EmulatorSettings().cartridge:
            raise ValueError(
                f"{directory} read the cartridge {run.settings.emulator.cartridge}"
            )

        if (
            (demonstration := run.settings.curriculum.demonstration)
            and demonstration.is_absolute()
        ):
            raise ValueError(f"{directory} followed the demonstration {demonstration}")

        if not (scores := tuple(map(Score.of, run.evaluated))):
            raise ValueError(f"{directory} holds no evaluation")

        if (baseline := run.baselined) is None:
            raise ValueError(f"{directory} holds no baseline")

        return cls.of(
            run,
            baseline = Score.of(baseline),
            goal     = run.settings.environment.goal,
            scores   = scores
        )

    @classmethod
    def seeded(cls, runs: Iterable[Self]) -> tuple[Self, ...]:
        """
        Orders `runs` by seed, so every estimate over them, and the
        generator drawing its resamples, holds whatever order the runs'
        names list in.
        """
        return tuple(sorted(runs, key=attrgetter("seed")))


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
    their goal.
    """

    beats: Estimate
    """
    The probability that a run of the agent beats a run of the baseline on
    mean return.
    """

    bedroom: Estimate | None
    """
    The probability that a run trained along the curriculum beats a run of
    the same agent trained from the bedroom on mean return, or `None` for
    runs trained from the bedroom or an agent with none.
    """

    curriculum: bool
    """
    Whether the runs started their training episodes along a demonstration.
    """

    reached: Estimate
    """
    The interquartile mean across the runs of the agent's share reaching
    their goal.
    """

    @classmethod
    def across(cls, runs: Iterable[Trained], bedroom: Iterable[Trained] = ()) -> Self:
        """
        Compares `runs`, all of one agent and one curriculum, against their
        baselines and, where they trained along the curriculum, against the
        same agent's runs from the `bedroom`, each interval over resamples
        drawn from the runs' seeds, each sample ordered by seed.
        """
        runs      = Trained.seeded(runs)
        bedroom   = Trained.seeded(bedroom)
        generator = default_rng([run.seed for run in runs])
        rewards   = array([run.last.reward for run in runs])

        return cls(
            agent    = runs[0].agent,
            baseline = Estimate.interquartile(
                array([run.baseline.reached for run in runs]),
                generator = generator
            ),
            bedroom = Estimate.improvement(
                rewards,
                array([run.last.reward for run in bedroom]),
                generator = generator
            ) if runs[0].curriculum and bedroom else None,
            beats = Estimate.improvement(
                rewards,
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

    random: Estimate | None
    """
    The interquartile mean across the runs' seeds of the baseline's share
    reaching their goal, each seed once, or `None` where no run is committed.
    """

    runs: tuple[Trained, ...]
    """
    Each run, in the order of its name.
    """

    @classmethod
    def read(cls, folder: Path = folder) -> Self:
        """
        Reads every run directory `folder` holds, none where it is missing.

        Raises:
            ValueError: Where the runs end their episodes at more than one
                        goal, whose shares no comparison sets side by side.
        """
        runs = tuple(
            Trained.read(directory)
            for directory in sorted(folder.iterdir() if folder.is_dir() else ())
        )
        Event.check_shared((run.goal for run in runs), f"the runs under {folder}")

        baselines = {run.seed: run.baseline.reached for run in Trained.seeded(runs)}
        group     = attrgetter("agent", "curriculum")
        groups    = {
            key: tuple(members)
            for key, members in groupby(sorted(runs, key=group), key=group)
        }

        return cls(
            comparisons = tuple(
                Comparison.across(members, groups.get((agent, False), ()))
                for (agent, _), members in groups.items()
            ),
            random = Estimate.interquartile(
                array(list(baselines.values())),
                generator = default_rng(list(baselines))
            ) if runs else None,
            runs = runs
        )
