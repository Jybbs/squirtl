"""
Defines the records the agents read and write:

- `Algorithm`, the agents a run trains
- `AgentSettings`, `PPOSettings`, and `PQNSettings`, every setting they read
- `Update` and `PolicyUpdate`, the measures one update reads

It also defines `accelerator`, which draws the default device, and `flush`,
which writes a file through the drive's cache.
"""

import fcntl

from collections.abc   import Iterable
from enum              import StrEnum, auto
from os                import fsync
from pydantic          import Field, PositiveFloat, PositiveInt, model_validator
from torch.accelerator import current_accelerator
from typing            import Annotated, Self

from squirtl.emulator.schemas import Record, UnitInterval

type Fraction = Annotated[float, Field(gt=0, le=1)]


def accelerator() -> str:
    """
    Names the accelerator torch reports as available, or the CPU where it
    reports none. Torch loads on this call alone under the lazy mode, and
    reading a run's record makes no call, since the record holds its device.
    """
    return str(current_accelerator(check_available=True) or "cpu")


class Algorithm(StrEnum):
    """
    The agents a run trains, each valued at its lowercase name.
    """

    DQN = auto()
    PPO = auto()
    PQN = auto()

    @property
    def measures(self) -> type[Measures]:
        """
        Reads the record of the measures one update of the agent reads,
        `PolicyUpdate` for PPO and `Update` for the deep Q-network and PQN.
        """
        return PolicyUpdate if self is Algorithm.PPO else Update

    @property
    def sampled(self) -> bool:
        """
        Reads whether the agent samples each action from a policy, as PPO
        does, where the deep Q-network and PQN choose epsilon-greedily.
        """
        return self is Algorithm.PPO


class Measures(Record):
    """
    The base of the measures one update reads, which an episode's record
    averages over the updates taken while it played.
    """

    def __str__(self) -> str:
        """
        Lists each measure after its name, at four significant digits, for
        the line an episode logs.
        """
        return ", ".join(f"{name} {value:.4g}" for name, value in self)

    @property
    def totals(self) -> tuple[float, ...]:
        """
        Lists each measure in the order the record declares them.
        """
        return tuple(dict(self).values())

    @classmethod
    def averaged(cls, count: int, totals: Iterable[float]) -> Self:
        """
        Divides each of `totals`, the sums of `count` updates' measures in
        the order the record declares them, by `count`.
        """
        return cls(
            **{
                name: total / count
                for name, total in zip(cls.model_fields, totals, strict=True)
            }
        )


class PPOSettings(Record):
    """
    The settings PPO alone reads, each a field of `AgentSettings.ppo` and a
    key under `[tool.squirtl.agent.ppo]` in `pyproject.toml`.
    """

    clip_range: PositiveFloat = 0.2
    """
    The distance from 1 at which each update clips the ratio of the new
    policy's probability of an action to the old one's, and from the old
    value at which it clips the new value, whose default is the clip range
    Pleines et al. train with on Pokémon Red.
    """

    epochs: PositiveInt = 3
    """
    The passes each update takes over the rollout, whose default is the
    epochs Pleines et al. train with.
    """

    learning_rate: PositiveFloat = 3e-4
    """
    The step size AdamW takes on every minibatch, held constant across the
    run, whose default is the learning rate Pleines et al. train with.
    """

    max_grad_norm: PositiveFloat = 0.5
    """
    The norm each minibatch's gradient is clipped to, whose default is the
    maximum gradient norm Pleines et al. train with.
    """

    minibatches: PositiveInt = 8
    """
    The minibatches each epoch splits the rollout into, whose default is the
    count Pleines et al. train with.
    """

    rollout_steps: PositiveInt = 2048
    """
    The steps each environment takes in a rollout, which each update then
    reads whole, whose default is the horizon Section III-B of Pleines et
    al. reports as more effective than horizons of 512 or 1024 steps.
    """

    trace_decay: UnitInterval = 0.95
    """
    The λ that weights each generalized advantage estimate of Schulman et
    al., whose default is the one Pleines et al. train with.
    """

    value_coefficient: PositiveFloat = 0.5
    """
    The weight of the value's loss beside the clipped objective, whose
    default is the coefficient Pleines et al. train with.
    """


class PQNSettings(Record):
    """
    The settings PQN alone reads, each a field of `AgentSettings.pqn` and a
    key under `[tool.squirtl.agent.pqn]` in `pyproject.toml`.
    """

    epochs: PositiveInt = 2
    """
    The passes each update takes over the rollout, whose default is the
    epochs of Gallici et al.'s Atari settings.
    """

    epsilon_end: UnitInterval = 0.001
    """
    The chance of a random action once exploration has annealed, whose
    default is the one Gallici et al.'s Atari settings finish at.
    """

    epsilon_start: UnitInterval = 1.0
    """
    The chance of a random action at the run's first step, whose default is
    the one Gallici et al.'s Atari settings start at.
    """

    exploration_fraction: Fraction = 0.1
    """
    The share of the run's steps over which the chance of a random action
    falls linearly from `epsilon_start` to `epsilon_end`, whose default is
    the decay of Gallici et al.'s Atari settings.
    """

    learning_rate: PositiveFloat = 2.5e-4
    """
    The step size RAdam takes on every minibatch, held constant across the
    run, whose default is the learning rate of Gallici et al.'s Atari
    settings.
    """

    max_grad_norm: PositiveFloat = 10.0
    """
    The norm each minibatch's gradient is clipped to, whose default is the
    maximum gradient norm of Gallici et al.'s Atari settings.
    """

    minibatches: PositiveInt = 32
    """
    The minibatches each epoch splits the rollout into, whose default is the
    count of Gallici et al.'s Atari settings.
    """

    rollout_steps: PositiveInt = 512
    """
    The steps each environment takes in a rollout, which each update then
    reads whole, whose default gives 8 environments the 4,096 samples of
    Gallici et al.'s Atari settings, their 128 environments of 32 steps.
    """

    trace_decay: UnitInterval = 0.65
    """
    The λ that weights each λ-return the network's values are trained
    toward, whose default is the one of Gallici et al.'s Atari settings.
    """


class AgentSettings(Record):
    """
    The settings the agents read, each a field of `RunSettings.agent` and
    a key under `[tool.squirtl.agent]` in `pyproject.toml`, where a field
    PQN and PPO share sits beside the deep Q-network's own and each reads a
    record of its own besides.
    """

    algorithm: Algorithm = Algorithm.DQN
    """
    The agent the run trains, the deep Q-network, PQN, or PPO.
    """

    batch_size: PositiveInt = 32
    """
    The transitions each update of the deep Q-network draws from replay
    memory, whose default follows Mnih et al.
    """

    capacity: PositiveInt = 100_000
    """
    The slots the deep Q-network's replay memory holds before overwriting
    the oldest, four per reset observation and one per step, whose default
    takes 606 MB for a 72 by 80 frame, a 48 by 48 grid, and a flag for each
    member of `Event`, the grid and the flags packed eight cells to a byte.
    """

    device: str = Field(default_factory=accelerator)
    """
    The device every network and batch sit on, which defaults to the
    accelerator torch reports and to the CPU where it reports none.
    """

    discount: Fraction = 0.997
    """
    The discount on the value of the state each step reaches, whose default
    is the one Pleines et al. settle on for this game after tuning over 0.99,
    0.997, 0.999, and 0.9995.
    """

    double_q: bool = True
    """
    Whether the deep Q-network's online network chooses the action at the
    state each step reaches and the target network values it, as van
    Hasselt et al.'s Double DQN does, where otherwise the target network
    does both, as Mnih et al.'s deep Q-network does.
    """

    environments: PositiveInt = 8
    """
    The environments PQN and PPO collect each rollout across in parallel,
    each in a worker process of its own, whose default suits the ten-core
    machine the runs train on, where both agents step more slowly across 4
    and PQN across 6, while neither steps measurably faster across 10 or 12.
    """

    epsilon_end: UnitInterval = 0.01
    """
    The deep Q-network's chance of a random action once exploration has
    annealed, whose default follows CleanRL's `dqn_atari.py`.
    """

    epsilon_start: UnitInterval = 1.0
    """
    The deep Q-network's chance of a random action at the run's first step,
    whose default follows CleanRL's `dqn_atari.py`.
    """

    exploration_fraction: Fraction = 0.1
    """
    The share of the run's steps over which the deep Q-network's chance of
    a random action falls linearly from `epsilon_start` to `epsilon_end`,
    whose default follows CleanRL's `dqn_atari.py`.
    """

    learning_rate: PositiveFloat = 1e-4
    """
    The step size Adam takes on every update of the deep Q-network, held
    constant across the run, whose default follows CleanRL's `dqn_atari.py`.
    """

    max_concurrency: PositiveInt | None = None
    """
    The most of PQN's and PPO's environments that step at once, which
    `AsyncVectorEnv` caps through a semaphore its workers share, or `None`
    for no cap, whose default leaves them uncapped, since a cap of 4, 6, or
    8 gives PPO no consistent gain in steps per second on the ten-core
    machine the runs train on.
    """

    max_grad_norm: PositiveFloat = 10.0
    """
    The norm each update of the deep Q-network clips its gradient to, whose
    default follows Stable-Baselines3's DQN.
    """

    ppo: PPOSettings = Field(default_factory=PPOSettings)
    """
    The settings PPO alone reads.
    """

    pqn: PQNSettings = Field(default_factory=PQNSettings)
    """
    The settings PQN alone reads.
    """

    sync_steps: PositiveInt = 1000
    """
    The environment steps between two copies of the deep Q-network's online
    network into its target network, whose default follows CleanRL's
    `dqn_atari.py`.
    """

    threads: PositiveInt | None = None
    """
    The threads PyTorch spreads each operation on the CPU across, set for
    the agent's whole process through `torch.set_num_threads` before its
    networks are built, whose default leaves the count PyTorch chooses.
    """

    update_steps: PositiveInt = 4
    """
    The environment steps between two updates of the deep Q-network, whose
    default is the update frequency Mnih et al. set.
    """

    warmup_steps: PositiveInt = 50_000
    """
    The environment steps whose transitions the deep Q-network's replay
    memory gathers before its first update, no fewer than `batch_size`,
    whose default is the replay start size Mnih et al. set.
    """

    @property
    def hyperparameters(self) -> PPOSettings | PQNSettings | None:
        """
        Reads the record of the settings `algorithm` alone reads, or `None`
        for the deep Q-network, whose own sit on this record.
        """
        return {Algorithm.PPO: self.ppo, Algorithm.PQN: self.pqn}.get(self.algorithm)

    @model_validator(mode="after")
    def verify(self) -> Self:
        """
        Refuses a `warmup_steps` below `batch_size`, since each step stores
        one transition and the first update draws `batch_size` of them from
        those replay memory holds. It also refuses a rollout of fewer than
        two samples per minibatch of the agent the run trains, since PPO
        normalizes each minibatch's advantages by their standard deviation.

        Raises:
            ValueError: Where either is short, which Pydantic raises as a
                        `ValidationError`.
        """
        if self.warmup_steps < self.batch_size:
            raise ValueError(
                f"a warm-up of {self.warmup_steps:,} steps gathers fewer "
                f"transitions than the {self.batch_size:,} each update draws"
            )

        if hyperparameters := self.hyperparameters:
            samples = self.environments * hyperparameters.rollout_steps

            if samples < 2 * hyperparameters.minibatches:
                raise ValueError(
                    f"a rollout of {samples:,} samples gives some of its "
                    f"{hyperparameters.minibatches:,} minibatches fewer than two"
                )

        return self


class PolicyUpdate(Measures):
    """
    The measures one update of PPO reads, each averaged over the minibatches
    of its epochs.
    """

    clipped: float
    """
    The share of the samples whose probability ratio lay outside the clip
    range.
    """

    entropy: float
    """
    The mean entropy of the policy over the samples.
    """

    kl: float
    """
    The mean of the ratio less 1 less its logarithm, Schulman's estimate of
    the Kullback-Leibler divergence of the old policy from the new.
    """

    policy_loss: float
    """
    The loss of the clipped objective.
    """

    value_loss: float
    """
    The loss of the value, its clipped squared error.
    """


class Update(Measures):
    """
    The loss and the mean value one update of the deep Q-network or PQN
    reads.
    """

    loss: float
    """
    The loss the update takes its gradient step on, the Huber loss for the
    deep Q-network and half the squared error for PQN.
    """

    value: float
    """
    The mean value the network gives each sampled action.
    """


def flush(descriptor: int):
    """
    Writes the file `descriptor` names through to the drive's storage,
    through `F_FULLFSYNC` where `fcntl` has it, as on macOS, whose `fsync`
    stops at the drive's own cache, and through `fsync` otherwise.
    """
    if full := getattr(fcntl, "F_FULLFSYNC", None):
        fcntl.fcntl(descriptor, full)
    else:
        fsync(descriptor)
