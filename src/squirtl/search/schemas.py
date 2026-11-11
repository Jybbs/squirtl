"""
Defines the records a search reads and writes, none of which needs PyTorch,
since a worker process imports this module:

- `Rollout`, the presses one worker plays from a snapshot, and `Ending`, what
  they reach
- `Particle`, one copy of the game the search plays forward
- `Frontier`, the particles and counters a checkpoint holds
- `Iteration`, one iteration as a line of a run's `iterations`
"""

from squirtl.emulator.schemas    import Record
from squirtl.environment.schemas import Snapshot


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
