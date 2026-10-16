"""
Defines the records the agent reads and writes:

- `AgentSettings`, every setting the agent reads
- `Batch`, the transitions one update draws from replay memory
- `Checkpoint`, the file holding everything a resumed run continues
  training from
"""

from pathlib           import Path
from pydantic          import Field, InstanceOf, PositiveFloat, PositiveInt, ValidatorFunctionWrapHandler, WrapValidator
from torch             import Tensor, load, no_grad, save
from torch.accelerator import current_accelerator
from typing            import Annotated, Self

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
    reset observation and one per step, whose default takes 606 MB with the
    grid and the flags packed eight cells to a byte.
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
    Everything a resumed run continues training from, which `torch.save`
    writes as one dictionary of tensors and plain values.
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
        Reads the checkpoint at `path` onto the CPU under `torch.load`'s
        default `weights_only=True`, which unpickles tensors and plain
        values alone, and validates each field.

        Raises:
            ValidationError: Where a field is missing or unknown, or a
                             network entry is no tensor.
        """
        return cls.model_validate(load(path, map_location="cpu"))

    def save(self, path: Path):
        """
        Writes each field as it is to `path` through `torch.save`, so each
        `state_dict` keeps its `_metadata`.
        """
        save(dict(self), path)
