"""
Defines the records the agent reads and writes:

- `AgentSettings`, every setting the agent reads
- `Batch`, the transitions one update draws from replay memory
- `Checkpoint`, the file holding everything a resumed run continues
  training from, replay memory included
- `Update`, the loss and the value one update reads
"""

from io                import BytesIO
from numpy             import load as load_npz, ndarray, save as save_npy
from os                import fsync
from pathlib           import Path
from pydantic          import Field, InstanceOf, PositiveFloat, PositiveInt, ValidatorFunctionWrapHandler, WrapValidator
from tempfile          import NamedTemporaryFile
from torch             import Tensor, load, no_grad, save
from torch.accelerator import current_accelerator
from typing            import Annotated, Self
from zipfile           import ZIP_ZSTANDARD, ZipFile

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

    discount: Fraction = 0.99
    """
    The discount on the value of the state each step reaches, whose default
    follows Mnih et al.
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
    def targets(self, discount: float, network: QNetwork) -> Tensor:
        """
        Values each draw at its reward plus `discount` times the highest
        value `network` gives the observation reached, or the reward alone
        where it terminated, recording no autograd graph.
        """
        return (
            self.rewards
            + discount * network(self.next_observations).amax(1) * ~self.terminated
        )

    def values(self, network: QNetwork) -> Tensor:
        """
        Reads the value `network` gives each draw's action on the
        observation it acted on.
        """
        return network(self.observations).gather(1, self.actions[:, None])[:, 0]


class Checkpoint(Record):
    """
    Everything a resumed run continues training from, which `save` writes as
    one `.npz` holding replay memory's arrays beside the agent.
    """

    exploration: dict[str, object]
    """
    The state of the generator choosing each random action.
    """

    online: StateDict
    """
    The online network's `state_dict`.
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

    step: int
    """
    The environment steps the agent has remembered.
    """

    target: StateDict
    """
    The target network's `state_dict`.
    """

    @classmethod
    def from_path(cls, path: Path) -> Self:
        """
        Reads the checkpoint `save` wrote at `path`, its `agent.pt` member
        onto the CPU and every other member as an array of `replay`, then
        validates each field. `torch.load` reads that member under its
        default `weights_only=True`, which unpickles tensors and plain
        values alone.

        Raises:
            ValidationError: Where a field is missing or unknown, or a
                             network entry is no tensor.
        """
        with load_npz(path) as archive:
            agent  = load(BytesIO(archive["agent.pt"]), map_location="cpu")
            replay = {
                name: archive[name] for name in archive.files if name != "agent.pt"
            }

        return cls.model_validate(agent | {"replay": replay})

    def save(self, path: Path):
        """
        Writes the checkpoint to `path` as an `.npz` whose members `zipfile`
        compresses with zstd, an `.npy` member for each array of `replay`
        beside an `agent.pt` member. `torch.save` writes that member
        holding every other field as it is, so each `state_dict` keeps its
        `_metadata`. The file takes its name once written whole and flushed
        to disk, so an interrupt leaves the checkpoint at `path` as it was.
        """
        with NamedTemporaryFile(delete_on_close=False, dir=path.parent) as file:
            with ZipFile(file, "w", ZIP_ZSTANDARD) as archive:
                with archive.open("agent.pt", "w") as member:
                    save({key: value for key, value in self if key != "replay"}, member)

                for name, array in self.replay.items():
                    # ZIP64 lets the frames of a large replay memory pass 2 GiB.
                    with archive.open(f"{name}.npy", "w", force_zip64=True) as member:
                        save_npy(member, array)

            file.flush()
            fsync(file.fileno())
            Path(file.name).replace(path)


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
