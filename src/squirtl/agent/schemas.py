"""
Defines the records the agents read and write:

- `Algorithm`, the agents a run trains
- `AgentSettings`, `PPOSettings`, and `PQNSettings`, every setting they read
- `Batch`, the transitions one update of the deep Q-network draws
- `Checkpoint`, `ReplayCheckpoint`, and `RolloutCheckpoint`, the file a resumed
  run continues training from, and `flush`, which writes it through the drive's
  cache
- `Update` and `PolicyUpdate`, the measures one update reads
- `Weights`, the part of a checkpoint an evaluation reads
"""

import fcntl

from collections.abc   import Iterable
from compression.zstd  import ZstdError
from enum              import StrEnum, auto
from gymnasium.spaces  import Dict
from io                import BytesIO
from numpy             import load as load_npz, ndarray, save as save_npy
from numpy.lib.npyio   import NpzFile
from os                import O_RDONLY, close, fsync, open as os_open
from pathlib           import Path
from pydantic          import Field, InstanceOf, PositiveFloat, PositiveInt, ValidatorFunctionWrapHandler, WrapValidator
from pydantic          import model_validator
from torch             import Tensor, default_generator, load, no_grad, save, set_num_threads
from torch.accelerator import current_accelerator
from torch.backends    import nnpack
from torch.nn          import Module
from torch.random      import fork_rng
from torch.serialization import safe_globals
from typing              import Annotated, Self
from zipfile             import BadZipFile, ZIP_ZSTANDARD, ZipFile

from squirtl.agent.networks   import ActorCritic, QNetwork
from squirtl.emulator.schemas import Record, UnitInterval

type Fraction  = Annotated[float, Field(gt=0, le=1)]
type StateDict = Annotated[
    dict[str, InstanceOf[Tensor]], WrapValidator(validate_in_place)
]


def validate_in_place(  # prose: ignore[unsorted-positionals]
    state   : object,
    handler : ValidatorFunctionWrapHandler
) -> object:
    """
    Validates each entry of `state` as a tensor through `handler`, then
    returns `state` itself, since the dict `handler` rebuilds drops the
    `_metadata` holding each module's version.
    """
    handler(state)

    return state


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

    def network(self, actions: int, space: Dict) -> Module:
        """
        Builds the network the agent acts through for `actions` actions over
        `space`, a `QNetwork` for the deep Q-network, one normalizing each
        layer for PQN, and an `ActorCritic` for PPO.
        """
        match self:
            case Algorithm.DQN : return QNetwork(actions, space)
            case Algorithm.PPO : return ActorCritic(actions, space)
            case Algorithm.PQN : return QNetwork(actions, space, normalized=True)


class Batch(Record):
    """
    The transitions one update draws from replay memory, each field on the
    device the settings name.
    """

    actions: InstanceOf[Tensor]
    """
    The action each draw took, a `(batch,)` tensor of `int64`.
    """

    rewards: InstanceOf[Tensor]
    """
    The reward each draw earned, a `(batch,)` tensor of `float32`.
    """

    terminated: InstanceOf[Tensor]
    """
    Whether each draw ended its episode, a `(batch,)` tensor of `bool`.
    """

    windows: dict[str, InstanceOf[Tensor]]
    """
    One `(batch, depth + 1, *element)` tensor per entry, its first `depth`
    elements the observation acted on and its last `depth` the one reached.
    """

    @property
    def next_observations(self) -> dict[str, Tensor]:
        """
        Slices the observation each draw reached out of `windows`.
        """
        return {key: window[:, 1:] for key, window in self.windows.items()}

    @property
    def observations(self) -> dict[str, Tensor]:
        """
        Slices the observation each draw acted on out of `windows`.
        """
        return {key: window[:, :-1] for key, window in self.windows.items()}

    @no_grad()
    def targets(self, chooser: QNetwork, discount: float, network: QNetwork) -> Tensor:
        """
        Values each draw at its reward plus `discount` times the value
        `network` gives the observation reached under the action `chooser`
        values highest there, or the reward alone where it terminated,
        recording no autograd graph. Where `chooser` is the online network
        and `network` the target network, the target is van Hasselt et al.'s
        Double DQN target, and where both are the target network, it is the
        highest value the target network gives, as Mnih et al.'s is, read
        from one pass of `network`.
        """
        reached = self.next_observations
        valued  = network(reached)
        chosen  = valued if chooser is network else chooser(reached)

        return (
            self.rewards
            + discount
                * valued.gather(1, chosen.argmax(1, keepdim=True))[:, 0]
                * ~self.terminated
        )

    def values(self, network: QNetwork) -> Tensor:
        """
        Reads the value `network` gives each draw's action on the
        observation it acted on.
        """
        return network(self.observations).gather(1, self.actions[:, None])[:, 0]


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

    trace_decay: UnitInterval = 0.65
    """
    The λ that weights each λ-return the network's values are trained
    toward, whose default is the one of Gallici et al.'s Atari settings.
    """


class Weights(Record, extra="ignore"):
    """
    The weights of the network an agent acts through and the step
    a checkpoint holds them at, which an evaluation reads from the
    checkpoint's `agent.pt` member alone.
    """

    online: StateDict
    """
    The `state_dict` of the network the agent acts through, the online
    network for the deep Q-network.
    """

    step: int
    """
    The environment steps the agent has taken.
    """

    @classmethod
    def from_path(cls, path: Path) -> Self:
        """
        Reads the checkpoint `save` wrote at `path` through `members`, then
        validates each field the record declares.

        Raises:
            ValidationError : Where a field is missing or a network entry is
                              no tensor.
            ValueError      : Where the file at `path` is cut short or
                              damaged, in its zip directory, a zip header, a
                              zstd frame, or a member, naming `path`.
        """
        try:
            # `numpy.load` leaves a file it opened itself open where `ZipFile` refuses
            # it, so the file is opened here and closed by this block.
            with path.open("rb") as file, load_npz(file) as archive:
                return cls.model_validate(cls.members(archive))
        except (
            BadZipFile, EOFError, KeyError, NotImplementedError, ZstdError
        ) as error:
            raise ValueError(f"{path} holds no whole checkpoint: {error}") from error

    @classmethod
    def members(cls, archive: NpzFile) -> dict[str, object]:
        """
        Reads the `agent.pt` member of `archive` onto the CPU, leaving
        every other member unread. `torch.load` reads it under its default
        `weights_only=True`, which unpickles tensors and plain values alone,
        with the `bytes` global allowed for the recording of an episode no
        step has played, since `torch.save` pickles an empty `bytes` through
        that global.
        """
        with safe_globals([bytes]):
            return load(BytesIO(archive["agent.pt"]), map_location="cpu")


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
    takes 606 MB for a 72 by 80 frame, a 48 by 48 grid, and four flags, the
    grid and the flags packed eight cells to a byte.
    """

    device: str = Field(
        default_factory = lambda: str(
            current_accelerator(check_available=True) or "cpu"
        )
    )
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

    rollout_steps: PositiveInt = 512
    """
    The steps each of PQN's and PPO's environments takes in a rollout, which
    each update then reads whole, whose default is the shortest of the 512,
    1024, and 2048 across which neither agent's steps per second differ
    measurably on the ten-core machine the runs train on, since a stop, a
    checkpoint, and an evaluation each land once an update ends.
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

    def network(self, actions: int, seed: int, space: Dict) -> Module:
        """
        Builds the network `algorithm` names on `device`, under a fork of
        PyTorch's global generator seeded from `seed`. It first turns NNPACK
        off for the whole process, which runs these networks' convolutions
        on the CPU slower than PyTorch's own, and sets the process's thread
        count to `threads`, where it names one.
        """
        nnpack.set_flags(False)

        if self.threads:
            set_num_threads(self.threads)

        with fork_rng(devices=[]):
            default_generator.manual_seed(seed)

            return self.algorithm.network(actions, space).to(self.device)

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

        samples = self.environments * self.rollout_steps

        if self.hyperparameters and samples < 2 * self.hyperparameters.minibatches:
            raise ValueError(
                f"a rollout of {samples:,} samples gives some of its "
                f"{self.hyperparameters.minibatches:,} minibatches fewer than two"
            )

        return self


class Checkpoint(Weights, extra="forbid"):
    """
    Everything a resumed run continues training from, the `Weights` an
    evaluation reads among it, which `save` writes as one `.npz` holding an
    `agent.pt` member beside an `.npy` member for each of its `arrays`.
    """

    optimizer: dict[str, object]
    """
    The optimizer's `state_dict`.
    """

    @property
    def arrays(self) -> dict[str, ndarray]:
        """
        Lists each array `save` writes as an `.npy` member of its own, none
        beyond what `agent.pt` holds.
        """
        return {}

    @property
    def contents(self) -> dict[str, object]:
        """
        Gathers what the `agent.pt` member holds, every field as it is, so
        each `state_dict` keeps its `_metadata`.
        """
        return dict(self)

    def save(self, path: Path):
        """
        Writes the checkpoint to `path` as an `.npz` whose members `zipfile`
        compresses with zstd, an `agent.pt` member that `torch.save` writes
        from `contents` beside an `.npy` member for each of `arrays`.

        The archive is written to the `.partial` file beside `path` and
        flushed through the drive's own cache, then takes the name `path`,
        whose directory is flushed in turn. An interrupt therefore leaves
        the checkpoint at `path` as it was, and the `.partial` file goes
        whether or not the write raised.
        """
        partial = path.with_name(f"{path.name}.partial")

        try:
            with partial.open("wb") as file:
                with ZipFile(file, "w", ZIP_ZSTANDARD) as archive:
                    with archive.open("agent.pt", "w") as member:
                        save(self.contents, member)

                    for name, array in self.arrays.items():
                        # ZIP64 lets the frames of a large replay memory pass 2 GiB.
                        with archive.open(
                            f"{name}.npy",
                            "w",
                            force_zip64 = True
                        ) as member:
                            save_npy(member, array)

                flush(file.fileno())

            partial.replace(path)
        finally:
            partial.unlink(missing_ok=True)

        directory = os_open(path.parent, O_RDONLY)

        try:
            fsync(directory)
        finally:
            close(directory)


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
    the Kullback-Leibler divergence of the new policy from the old.
    """

    policy_loss: float
    """
    The loss of the clipped objective.
    """

    value_loss: float
    """
    The loss of the value, its clipped squared error.
    """


class ReplayCheckpoint(Checkpoint):
    """
    Everything a resumed run of the deep Q-network continues training from,
    replay memory's arrays written as members of their own.
    """

    exploration: dict[str, object]
    """
    The state of the generator choosing each random action.
    """

    replay: dict[str, InstanceOf[ndarray]]
    """
    Each array replay memory holds, named as `Replay.arrays` names it.
    """

    sampling: dict[str, object]
    """
    The state of the generator drawing each batch from replay memory.
    """

    target: StateDict
    """
    The target network's `state_dict`.
    """

    @property
    def arrays(self) -> dict[str, ndarray]:
        """
        Lists replay memory's arrays.
        """
        return self.replay

    @property
    def contents(self) -> dict[str, object]:
        """
        Gathers every field but `replay`, as `Checkpoint.contents` does.
        """
        return {
            key: value for key, value in super().contents.items() if key != "replay"
        }

    @classmethod
    def members(cls, archive: NpzFile) -> dict[str, object]:
        """
        Reads `agent.pt` as `Weights.members` does and every other member of
        `archive` as an array of `replay`.
        """
        return super().members(archive) | {
            "replay":
                {name: archive[name] for name in archive.files if name != "agent.pt"}
        }


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


class RolloutCheckpoint(Checkpoint):
    """
    Everything a resumed run of PQN or PPO continues training from on the
    agent's side.
    """

    generator: dict[str, object]
    """
    The state of the generator every random draw of the agent comes from.
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
