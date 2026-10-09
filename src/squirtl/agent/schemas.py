"""
Defines the records the agent reads and writes:

- `AgentSettings`, every setting the agent reads
- `Batch`, the transitions one update draws from replay memory
- `Checkpoint`, the file holding everything a resumed run continues
  training from
"""

from dataclasses       import dataclass
from pathlib           import Path
from pydantic          import BaseModel, Field, PositiveFloat, PositiveInt
from torch             import Tensor, load, no_grad, save
from torch.accelerator import current_accelerator
from typing            import Annotated, Self

from squirtl.agent.networks import QNetwork

type Fraction = Annotated[float, Field(gt=0, le=1)]

type Probability = Annotated[float, Field(ge=0, le=1)]


class AgentSettings(
    BaseModel, extra="forbid", frozen=True, use_attribute_docstrings=True
):
    """
    The settings the agent reads, each a `--agent.<field>` flag on a
    command taking `RunSettings` and a key under `[tool.squirtl.agent]`
    in `pyproject.toml`.
    """

    batch_size: PositiveInt = 32
    """
    The transitions each update draws from replay memory, whose default
    follows Mnih et al.
    """

    capacity: PositiveInt = 100_000
    """
    The frames replay memory holds before it overwrites the oldest, four for
    each episode's reset observation and one for each step after it, whose
    default holds 72 by 80 frames in 576 MB.
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

    epsilon_end: Probability = 0.01
    """
    The chance of a random action once exploration has annealed, whose
    default follows CleanRL's `dqn_atari.py`.
    """

    epsilon_start: Probability = 1.0
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


@dataclass(frozen=True, kw_only=True)
class Batch:
    """
    The transitions one update draws from replay memory, each field a tensor
    on the device the settings name, with the frames of both stacks a draw
    reads held once in `window`.
    """

    actions    : Tensor  # (batch,) int64
    rewards    : Tensor  # (batch,) float32
    terminated : Tensor  # (batch,) bool
    window     : Tensor  # (batch, 5, 72, 80) uint8

    @property
    def next_observations(self) -> Tensor:
        """
        Slices the stacks each draw's action reached out of `window`, its
        frames after the first.
        """
        return self.window[:, 1:]

    @property
    def observations(self) -> Tensor:
        """
        Slices the stacks each draw's action was taken on out of `window`,
        its frames before the last.
        """
        return self.window[:, :-1]

    @no_grad()
    def targets(self, discount: float, network: QNetwork) -> Tensor:
        """
        Values each draw at its reward plus `discount` times the highest
        value `network` gives the stack its action reached, or at its reward
        alone where the step terminated the episode, recording no autograd
        graph.
        """
        return (
            self.rewards
            + discount * network(self.next_observations).amax(1) * ~self.terminated
        )

    def values(self, network: QNetwork) -> Tensor:
        """
        Reads the value `network` gives each draw's action on the stack it
        was taken on.
        """
        return network(self.observations).gather(1, self.actions[:, None])[:, 0]


@dataclass(frozen=True, kw_only=True)
class Checkpoint:
    """
    Everything a resumed run continues training from, meaning both networks,
    the optimizer, the step count, and the state of each generator the agent
    draws from, which `torch.save` writes as one dictionary of tensors and
    plain values.
    """

    exploration : dict[str, object]
    online      : dict[str, Tensor]
    optimizer   : dict[str, object]
    sampling    : dict[str, object]
    step        : int
    target      : dict[str, Tensor]

    @classmethod
    def from_path(cls, path: Path) -> Self:
        """
        Reads the checkpoint at `path` onto the CPU under `torch.load`'s
        default `weights_only=True`, which unpickles tensors and plain
        values alone.
        """
        return cls(**load(path, map_location="cpu"))

    def save(self, path: Path):
        """
        Writes the checkpoint to `path` through `torch.save`.
        """
        save(vars(self), path)
