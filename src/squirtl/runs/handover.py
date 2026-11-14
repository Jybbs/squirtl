"""
Defines the records a resumed training run continues from:

- `Handover`, what it takes over from the stopped run it continues
- `Moments`, `Slot`, and `VectorCheckpoint`, everything it continues from
  where the run trains PQN or PPO, its `Curriculum` included

It also defines `Tally`, the sums of the measures each environment's episode
averages, which `Trainer` keeps as it trains.
"""

from numpy    import int64, zeros
from pydantic import NonNegativeInt

from squirtl.agent.checkpoint    import Checkpoint, RolloutCheckpoint
from squirtl.agent.schemas       import Measures
from squirtl.emulator.schemas    import Record
from squirtl.environment.schemas import Recording
from squirtl.evaluation.schemas  import Evaluation
from squirtl.runs.curriculum     import Syllabus
from squirtl.runs.schemas        import Run


class Handover(Record):
    """
    What a resumed run takes over from the stopped run it continues, read
    whole before the new run writes anything, so a resume refused for any of
    it leaves no directory behind.
    """

    baseline: Evaluation | None
    """
    The random baseline's evaluation the stopped run's `baseline` holds, or
    `None` where it played none.
    """

    checkpoint: Checkpoint
    """
    The stopped run's last checkpoint, which the run restores.
    """

    episodes: list[str]
    """
    The line of each episode written before the checkpoint, as the stopped
    run's `episodes` holds it.
    """

    evaluations: list[Evaluation]
    """
    Each evaluation of the agent at the checkpoint's step or before it.
    """

    name: str
    """
    The stopped run's name, which the new run records under `resumes`.
    """

    @property
    def evaluated(self) -> int:
        """
        Reads the step of the last evaluation carried over, or 0 where none
        is.
        """
        return self.evaluations[-1].step if self.evaluations else 0

    def write(self, run: Run):
        """
        Writes into `run` what the handover carries over, each episode's
        line as the stopped run wrote it, each evaluation, and the random
        baseline's where it played one.
        """
        run.carry(self.episodes, run.episodes)
        run.append(run.evaluations, *self.evaluations)

        if self.baseline is not None:
            run.baseline.write_text(self.baseline.model_dump_json(), encoding="utf-8")


class Moments(Record):
    """
    The statistics `NormalizeReward` keeps of the discounted returns, by the
    square root of whose variance it divides each reward.
    """

    count: float
    """
    The count of returns, which starts from a small positive value.
    """

    mean: float
    """
    The returns' running mean.
    """

    var: float
    """
    The returns' running variance.
    """


class Slot(Record):
    """
    One environment of a run of PQN or PPO as a checkpoint leaves it, in the
    middle of an episode.
    """

    count: int
    """
    The updates taken while the episode played.
    """

    generator: dict[str, object]
    """
    The state of the generator the environment's next reset draws its
    `timer_div` from.
    """

    recording: Recording
    """
    The episode the environment is playing, unfinished, which a resumed run
    plays back through the environment's wrappers.
    """

    returned: float
    """
    The discounted return `NormalizeReward` keeps for the episode.
    """

    totals: list[float]
    """
    The sum of each measure of the updates taken while the episode played.
    """


class Tally:
    """
    The sums of the measures of the updates taken while each environment's
    episode played, beside the count of those updates, which an episode's
    record averages once it ends.
    """

    def __init__(self, environments: int, measures: type[Measures]):
        """
        Starts every environment's sums at 0 for the fields of `measures`.
        """
        self.counts   = zeros(environments, int64)
        self.measures = measures
        self.totals   = zeros((environments, len(measures.model_fields)))

    def add(self, update: Measures):
        """
        Adds the measures of `update` to every environment's sums.
        """
        self.counts += 1
        self.totals += update.totals

    def take(self, slot: int) -> Measures | None:
        """
        Averages the sums of the environment at `slot` and starts them again
        at 0, as its episode ends.

        Returns:
            Each measure averaged over the updates taken while the episode
            played, or `None` where none was.
        """
        count, totals     = self.counts[slot].item(), self.totals[slot].tolist()
        self.counts[slot] = 0
        self.totals[slot] = 0

        return self.measures.averaged(count, totals) if count else None


class VectorCheckpoint(RolloutCheckpoint):
    """
    Everything a resumed run of PQN or PPO continues training from, the
    environments' side beside the agent's.
    """

    episodes: NonNegativeInt
    """
    The count of episodes the run had written to its `episodes`.
    """

    moments: Moments
    """
    The statistics `NormalizeReward` scales each reward by.
    """

    slots: list[Slot]
    """
    Each environment, in the order the run steps them.
    """

    syllabus: Syllabus | None = None
    """
    The curriculum moving each start along the demonstration, or `None`
    where the run follows none.
    """

    @property
    def contents(self) -> dict[str, object]:
        """
        Gathers every field as `Checkpoint.contents` does, the moments, each
        slot, and the syllabus as plain values, which `torch.load` reads
        under `weights_only=True`.
        """
        return super().contents | self.model_dump(
            include = {"moments", "slots", "syllabus"}
        )
