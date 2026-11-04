"""
Defines the records the agent reads and writes:

- `AgentSettings`, every setting the agent reads
- `Update`, the loss and the value one update reads

It also defines `accelerator`, which draws the default device, and `flush`,
which writes a file through the drive's cache.
"""

import fcntl

from os       import fsync
from pydantic import Field, PositiveFloat, PositiveInt, model_validator
from typing   import Annotated, Self

from squirtl.emulator.schemas import Record, UnitInterval

type Fraction = Annotated[float, Field(gt=0, le=1)]


def accelerator() -> str:
    """
    Names the accelerator torch reports as available, or the CPU where it
    reports none. It imports torch only on this call, and reading a run's
    record draws no default, since the record holds its device.
    """
    from torch.accelerator import current_accelerator

    return str(current_accelerator(check_available=True) or "cpu")


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

    device: str = Field(default_factory=accelerator)
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
