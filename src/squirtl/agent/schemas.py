"""
Defines the records the agent reads and writes:

- `AgentSettings`, every setting the agent reads
- `Batch`, the transitions one update draws from replay memory
- `Checkpoint`, the file holding everything a resumed run continues
  training from, replay memory included, and `flush`, which writes a file
  through the drive's cache
- `Update`, the loss and the value one update reads
- `Weights`, the online network's weights and their step, which an
  evaluation reads from a checkpoint alone
"""

import fcntl

from compression.zstd  import ZstdError
from io                import BytesIO
from numpy             import load as load_npz, ndarray, save as save_npy
from numpy.lib.npyio   import NpzFile
from os                import O_RDONLY, close, fsync, open as os_open
from pathlib           import Path
from pydantic          import Field, InstanceOf, PositiveFloat, PositiveInt, ValidatorFunctionWrapHandler, WrapValidator
from pydantic          import model_validator
from torch             import Tensor, load, no_grad, save
from torch.accelerator import current_accelerator
from typing            import Annotated, Self
from zipfile           import BadZipFile, ZIP_ZSTANDARD, ZipFile

from squirtl.agent.networks   import QNetwork
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


class AgentSettings(Record):
    """
    The settings the agent reads, each a field of `RunSettings.agent` and a
    key under `[tool.squirtl.agent]` in `pyproject.toml`.
    """

    batch_size: PositiveInt = 32
    """
    The transitions each update draws from replay memory, whose default
    follows Mnih et al.
    """

    capacity: PositiveInt = 100_000
    """
    The slots replay memory holds before overwriting the oldest, four per
    reset observation and one per step, whose default takes 606 MB for a 72
    by 80 frame, a 48 by 48 grid, and four flags, the grid and the flags
    packed eight cells to a byte.
    """

    device: str = Field(
        default_factory = lambda: str(
            current_accelerator(check_available=True) or "cpu"
        )
    )
    """
    The device both networks and every batch sit on, which defaults to the
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
    Whether the online network chooses the action at the state each step
    reaches and the target network values it, as van Hasselt et al.'s
    Double DQN does, where otherwise the target network does both, as Mnih
    et al.'s deep Q-network does.
    """

    epsilon_end: UnitInterval = 0.01
    """
    The chance of a random action once exploration has annealed, whose
    default follows CleanRL's `dqn_atari.py`.
    """

    epsilon_start: UnitInterval = 1.0
    """
    The chance of a random action at the run's first step, whose default
    follows CleanRL's `dqn_atari.py`.
    """

    exploration_fraction: Fraction = 0.1
    """
    The share of the run's steps over which the chance of a random action
    falls linearly from `epsilon_start` to `epsilon_end`, whose default
    follows CleanRL's `dqn_atari.py`.
    """

    learning_rate: PositiveFloat = 1e-4
    """
    The step size Adam takes on every update, held constant across the run,
    whose default follows CleanRL's `dqn_atari.py`.
    """

    max_grad_norm: PositiveFloat = 10.0
    """
    The norm each update's gradient is clipped to, whose default follows
    Stable-Baselines3's DQN.
    """

    sync_steps: PositiveInt = 1000
    """
    The environment steps between two copies of the online network into the
    target network, whose default follows CleanRL's `dqn_atari.py`.
    """

    threads: PositiveInt | None = None
    """
    The threads PyTorch spreads each operation on the CPU across, set for
    the agent's whole process through `torch.set_num_threads` before its
    networks are built, whose default leaves the count PyTorch chooses.
    """

    update_steps: PositiveInt = 4
    """
    The environment steps between two updates of the online network, whose
    default is the update frequency Mnih et al. set.
    """

    warmup_steps: PositiveInt = 50_000
    """
    The environment steps whose transitions replay memory gathers before the
    first update, no fewer than `batch_size`, whose default is the replay
    start size Mnih et al. set.
    """

    @model_validator(mode="after")
    def verify(self) -> Self:
        """
        Refuses a `warmup_steps` below `batch_size`, since each step stores
        one transition and the first update draws `batch_size` of them from
        those replay memory holds.

        Raises:
            ValueError: Where it is below, which Pydantic raises as a
                        `ValidationError`.
        """
        if self.warmup_steps < self.batch_size:
            raise ValueError(
                f"a warm-up of {self.warmup_steps:,} steps gathers fewer "
                f"transitions than the {self.batch_size:,} each update draws"
            )

        return self


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


class Weights(Record, extra="ignore"):
    """
    The online network's weights and the step a checkpoint holds them at,
    which an evaluation reads from the checkpoint's `agent.pt` member alone.
    """

    online: StateDict
    """
    The online network's `state_dict`.
    """

    step: int
    """
    The environment steps the agent has remembered.
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
        replay memory's members unread. `torch.load` reads it under its
        default `weights_only=True`, which unpickles tensors and plain
        values alone.
        """
        return load(BytesIO(archive["agent.pt"]), map_location="cpu")


class Checkpoint(Weights, extra="forbid"):
    """
    Everything a resumed run continues training from, the `Weights` an
    evaluation reads among it, which `save` writes as one `.npz` holding
    replay memory's arrays beside an `agent.pt` member holding the rest.
    """

    exploration: dict[str, object]
    """
    The state of the generator choosing each random action.
    """

    optimizer: dict[str, object]
    """
    Adam's `state_dict`.
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

    def save(self, path: Path):
        """
        Writes the checkpoint to `path` as an `.npz` whose members `zipfile`
        compresses with zstd, an `.npy` member for each array of `replay`
        beside an `agent.pt` member. `torch.save` writes that member
        holding every other field as it is, so each `state_dict` keeps its
        `_metadata`.

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
                        save(
                            {key: value for key, value in self if key != "replay"},
                            member
                        )

                    for name, array in self.replay.items():
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


class Update(Record):
    """
    The loss and the mean value one update reads from the batch it draws,
    which an episode's record averages over the updates its steps take.
    """

    loss: float
    """
    The Huber loss the update takes its gradient step on.
    """

    value: float
    """
    The mean value the online network gives each draw's action.
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
