"""
Defines the records a search reads and writes, none of which needs PyTorch,
since a worker process imports this module:

- `Range`, the fewest and the most of a count a search draws
- `SearchSettings`, every setting a search reads
- `Rollout`, the presses one worker plays from a snapshot, and `Ending`, what
  they reach
- `Particle`, one copy of the game the search plays forward
- `Frontier`, the particles and counters a checkpoint holds
- `Iteration`, one iteration as a line of a run's `iterations`
"""

from pydantic import AfterValidator, Field, PositiveFloat, PositiveInt
from typing   import Annotated

from squirtl.emulator.schemas    import Record, UnitInterval, processors
from squirtl.environment.schemas import Snapshot
from squirtl.reward.schemas      import Event

type Range = Annotated[tuple[PositiveInt, PositiveInt], AfterValidator(ascending)]


def ascending(bounds: tuple[int, int]) -> tuple[int, int]:
    """
    Refuses a range whose fewest exceeds its most, returning `bounds` as
    they are otherwise.

    Raises:
        ValueError: Where it does, which Pydantic raises as a
                    `ValidationError` naming the field.
    """
    if bounds[0] > bounds[1]:
        raise ValueError(f"the range {bounds} runs backward")

    return bounds


class Ending(Record):
    """
    What one rollout reached, which the worker returns.
    """

    dead: bool
    """
    Whether the rollout earned no reward and ended on the screen and the map
    position it started from.
    """

    frames: bytes
    """
    The newest frame each press observed, in order, as `uint8` bytes.
    """

    presses: bytes
    """
    The action each press took, leaving out any the rollout stopped short
    of.
    """

    reward: float
    """
    The reward the flags set by the rollout's end have earned, the novelty
    of every position left out.
    """

    snapshot: Snapshot
    """
    The environment the rollout ended on.
    """


class Iteration(Record):
    """
    One iteration of a search as a run records it on a line of its
    `iterations`.
    """

    length: int
    """
    The presses of the demonstration the iteration leaves.
    """

    loss: float | None
    """
    The mean squared error over the predictor's updates that followed the
    iteration, or `None` where none did.
    """

    memory: int
    """
    The bytes the tree holds, its nodes and the states it keeps.
    """

    nodes: int
    """
    The nodes the tree holds.
    """

    positions: int
    """
    The positions the winner's path reached.
    """

    presses: int
    """
    The presses the search's rollouts have taken by the iteration's end.
    """

    reward: float
    """
    The winner's reward, which the demonstration earns.
    """

    seconds: float
    """
    The wall time of the iteration, in seconds.
    """


class Particle(Record):
    """
    One copy of the game the search plays forward, which a group ranks by
    its reward and then its uncertainty.
    """

    node: int
    """
    The node of the tree the particle occupies.
    """

    reward: float
    """
    The reward the flags set on the way to its node have earned.
    """

    score: float
    """
    The uncertainty the predictor last gave its frames.
    """

    snapshot: Snapshot
    """
    The environment at its node.
    """

    @property
    def rank(self) -> tuple[float, float]:
        """
        Pairs the reward with the uncertainty, the order Mhammedi and
        Cohan's lexicographic argmax compares the two in.
        """
        return self.reward, self.score

    @property
    def terminated(self) -> bool:
        """
        Reads whether `EVENT_GOT_STARTER` is set at its node.
        """
        return Event.EVENT_GOT_STARTER in self.snapshot.tally.events


class Rollout(Record):
    """
    What one worker plays, the actions it presses from a snapshot.
    """

    presses: bytes
    """
    The action each press takes, one byte a press.
    """

    snapshot: Snapshot
    """
    The environment the presses start from.
    """

    halting: bool = True
    """
    Whether the presses stop once they earn reward, where otherwise every
    one of them plays, as bringing back a node of the tree does.
    """


class SearchSettings(Record):
    """
    The settings a search reads, each a field of `RunSettings.search` and a
    key under `[tool.squirtl.search]` in `pyproject.toml`. The population's
    defaults are the Montezuma's Revenge column of Table 5 in Mhammedi
    and Cohan's "Decoupling Exploration and Policy Optimization", and the
    predictor's are their Appendix A.3.
    """

    batch_size: PositiveInt = 128
    """
    The frame stacks each update of the predictor draws, whose default
    follows Mhammedi and Cohan's Appendix A.3.
    """

    capacity: PositiveInt = 100_000
    """
    The frames replay memory holds for the predictor, one per slot, under
    1 GB at the default frame shape.
    """

    epsilon: UnitInterval = 0.2
    """
    The chance a press takes a random action in place of the one its
    rollout holds, whose default follows Mhammedi and Cohan's Appendix A.2.
    """

    groups: PositiveInt = 4
    """
    The groups of particles the search evolves, Mhammedi and Cohan's M.
    """

    inner_steps: Range = (5, 15)
    """
    The fewest and the most presses of one rollout, Mhammedi and Cohan's
    range of T.
    """

    learning_rate: PositiveFloat = 3e-4
    """
    The step size Adam takes on the predictor, whose default follows
    Mhammedi and Cohan's Appendix A.3.
    """

    outer_steps: Range = (10, 20)
    """
    The fewest and the most rollouts each particle plays in one iteration,
    Mhammedi and Cohan's range of K.
    """

    particles: PositiveInt = 32
    """
    The particles each group holds, Mhammedi and Cohan's N.
    """

    rollback: Range = (1, 3)
    """
    The fewest and the most generations a particle moves up the tree once
    every particle of its group is dead, Mhammedi and Cohan's range of k.
    """

    update_steps: PositiveInt = 44
    """
    The presses between updates of the predictor, whose default is the
    ratio of Mhammedi and Cohan's Table 6, 2.28 million updates over 400
    million frames at their action repeat of 4.
    """

    workers: PositiveInt = Field(default_factory=processors)
    """
    The worker processes the rollouts run across, which defaults to the
    CPUs the process may use.
    """


class Frontier(Record):
    """
    What a search holds at the end of an iteration beside its arrays and its
    networks, which a checkpoint writes as JSON.
    """

    groups: list[Particle]
    """
    The particle each group consolidated on, in the order of the groups.
    """

    iterations: int
    """
    The iterations the search has finished.
    """

    planning: dict[str, object]
    """
    The state of the generator drawing each rollout, each outer step's
    count, and each rollback.
    """

    presses: int
    """
    The presses the search's rollouts have taken.
    """

    states: dict[int, Snapshot]
    """
    The environment the tree keeps at each node holding one.
    """

    winner: Particle
    """
    The best particle across the groups so far.
    """
