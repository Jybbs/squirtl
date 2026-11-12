"""
Defines the records a search reads and writes, none of which needs PyTorch,
since a worker process imports this module:

- `SearchRollout`, the presses one worker plays from a snapshot, and
  `Ending`, what they reach
- `Particle`, one copy of the game the search plays forward
- `Frontier`, the particles and counters a checkpoint holds
- `Iteration`, one iteration as a line of a run's `iterations`
- `SearchSettings`, the settings a search reads
"""

from pydantic import Field, PositiveFloat, PositiveInt
from typing   import Self

from squirtl.emulator.schemas    import Range, Record, UnitInterval, processors
from squirtl.environment.schemas import Snapshot


class Ending(Record):
    """
    What one rollout reached, which the worker returns.
    """

    dead: bool
    """
    Whether the rollout blacked out, or set no flag and ended on the map
    position and the `wTileMap` it started from.
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
    The mean squared error over the predictor's updates run while the
    iteration played, those owed for the iterations before it, or `None`
    where none were.
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


class SearchRollout(Record):
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
    The settings a search over save states reads, each a field of
    `RunSettings.search` and a key under `[tool.squirtl.search]` in
    `pyproject.toml`. The population's defaults are the Montezuma's Revenge
    column of Table 5 in Mhammedi and Cohan's "Decoupling Exploration and
    Policy Optimization", the chance of a random press their Appendix A.2's,
    and the predictor's their Appendix A.3's, its updates per press taken
    from their Table 6.
    """

    batch_size: PositiveInt = 128
    """
    The frame stacks each update of the predictor draws, whose default
    follows Mhammedi and Cohan's Appendix A.3.
    """

    capacity: PositiveInt = 512_000
    """
    The frames replay memory holds for the predictor, one per slot, about
    2.95 GB at the default frame shape, whose default is the 512,000 entries
    of Mhammedi and Cohan's Appendix A.3, each an observation there and a
    frame here, so a stored start stack takes four.
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

    inner_steps: Range[PositiveInt] = (5, 15)
    """
    The fewest and the most presses of one rollout, Mhammedi and Cohan's
    range of T.
    """

    learning_rate: PositiveFloat = 3e-4
    """
    The step size Adam takes on the predictor, whose default follows
    Mhammedi and Cohan's Appendix A.3.
    """

    outer_steps: Range[PositiveInt] = (10, 20)
    """
    The fewest and the most rollouts each particle plays in one iteration,
    Mhammedi and Cohan's range of K.
    """

    particles: PositiveInt = 32
    """
    The particles each group holds, Mhammedi and Cohan's N.
    """

    rollback: Range[PositiveInt] = (1, 3)
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

    @classmethod
    def of(cls, ending: Ending, node: int, score: float) -> Self:
        """
        Places the particle a rollout's `ending` leaves on `node`, holding
        the reward and the environment it reached and the uncertainty
        `score`.
        """
        return cls(
            node     = node,
            reward   = ending.reward,
            score    = score,
            snapshot = ending.snapshot
        )


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
