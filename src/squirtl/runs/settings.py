"""
Defines the settings one run reads:

- `RunSettings`, every setting the run reads, `CurriculumSettings` among
  them, beside `TrainingSettings` and `SearchRunSettings`, the parts of it
  `squirtl train` and `squirtl search` each parse
- `Stream`, the streams of random draws the run makes, each seeded from
  `RunSettings.seed`
"""

from cyclopts     import Parameter
from enum         import StrEnum, auto
from numpy        import uint64
from numpy.random import SeedSequence
from pathlib      import Path
from pydantic     import Field, NonNegativeFloat, NonNegativeInt, PositiveFloat, PositiveInt, model_validator
from typing       import Annotated, ClassVar, Self

from squirtl.agent.schemas       import AgentSettings, Algorithm
from squirtl.emulator.schemas    import EmulatorSettings, Range, Record, UnitInterval
from squirtl.environment.schemas import EnvironmentSettings
from squirtl.evaluation.schemas  import EvaluationSettings
from squirtl.reward.schemas      import RewardSettings
from squirtl.search.schemas      import SearchSettings


class CurriculumSettings(Record):
    """
    The settings of the curriculum that starts each training episode
    along a demonstration and moves the start back toward Blue's
    bedroom, each a field of `RunSettings.curriculum` and a key under
    `[tool.squirtl.curriculum]` in `pyproject.toml`. Every default but
    `demonstration` is the one Mhammedi and Cohan's Table 8 sets for the
    backward algorithm of their Appendix B.
    """

    back: Range[PositiveFloat] = (0.25, 0.75)
    """
    The least and the most a window moves back, each a multiple of `window`,
    between which each move draws uniformly, whose default is the decrease
    multipliers of Mhammedi and Cohan's Table 8.
    """

    buffer: PositiveInt = 500
    """
    The steps an episode from a start takes beyond `multiplier` times the
    moving average of successful lengths before it truncates, whose default
    is the rollout length buffer of Mhammedi and Cohan's Table 8.
    """

    completion: UnitInterval = 0.95
    """
    The share of the recent episodes from a window reaching Blue's bedroom
    that have to succeed before its segment counts as solved, whose default
    is the completion threshold of Mhammedi and Cohan's Table 8.
    """

    demonstration: Path | None = None
    """
    The directory of the run whose shortest episode reaching the goal each
    training episode starts along, a run ending its episodes at the same
    goal, or `None` to start every episode in Blue's bedroom.
    """

    forward: Range[PositiveFloat] = (0.5, 1.0)
    """
    The least and the most a window moves forward, each a multiple of
    `window`, between which each move draws uniformly, whose default is the
    increase multipliers of Mhammedi and Cohan's Table 8.
    """

    multiplier: PositiveFloat = 2.0
    """
    The multiple of the moving average of successful lengths an episode
    from a start takes before `buffer` and then truncates, whose default is
    the early termination multiplier of Mhammedi and Cohan's Table 8.
    """

    recent: PositiveInt = 32
    """
    The episodes from a window whose share of successes moves it, after
    which the count starts again, whose default is the minimum rollouts for
    an update of Mhammedi and Cohan's Table 8.
    """

    required: UnitInterval = 0.2
    """
    The share of the recent episodes from a window that have to succeed for
    it to move back, where a smaller share moves it forward, whose default
    is the required success rate of Mhammedi and Cohan's Table 8.
    """

    smoothing: UnitInterval = 0.9
    """
    The weight the moving average of successful lengths gives each new
    length, the smoothing constant of single exponential smoothing in
    section 6.4.3.1 of the NIST/SEMATECH e-Handbook of Statistical Methods,
    whose default is the smoothing factor of Mhammedi and Cohan's Table 8.
    """

    tolerance: NonNegativeFloat = 0.0
    """
    The reward an episode from a start may fall short of the
    demonstration's from the same step and still succeed, whose default is
    the failure reward tolerance of Mhammedi and Cohan's Table 8.
    """

    window: PositiveInt = 25
    """
    The steps of the demonstration each segment's window spans back from
    its latest start, whose default is the start delta window of Mhammedi
    and Cohan's Table 8.
    """

    @model_validator(mode="after")
    def verify(self) -> Self:
        """
        Refuses a `required` share above `completion`.

        Raises:
            ValueError: Where it lies above, which Pydantic raises as a
                        `ValidationError`.
        """
        if self.required > self.completion:
            raise ValueError(
                f"a required share of {self.required} passes the completion share "
                f"of {self.completion}"
            )

        return self


class Stream(StrEnum):
    """
    The streams of random draws a run makes, each starting from a seed of
    its own, so no stream repeats the draws of another.
    """

    AGENT       = auto()
    ENVIRONMENT = auto()
    EVALUATION  = auto()
    WINDOW      = auto()
    SEARCH      = auto()


class RunSettings(Record):
    """
    The settings one run reads, where each field is a flag on any
    command that flattens the record through `Parameter(name="*")` and
    a key under `[tool.squirtl]` in `pyproject.toml`. A field holding
    a subject's record takes that record's fields as flags under its
    name (`--emulator.cartridge`) and as keys of a table of its own
    (`[tool.squirtl.emulator]`). A bare `*` before the record in the
    command's signature keeps every field keyword-only, so no bare token
    fills one.
    """

    machine: ClassVar[dict[str, set[str]]] = {
        "agent"      : {"device"},
        "evaluation" : {"environments"},
        "search"     : {"workers"}
    }
    """
    The fields under each subject whose default follows the machine a run
    starts on, the agent's device, the environments an evaluation plays
    across, and the workers a search plays across, each left out of the
    defaults the site's pages state.
    """

    agent: AgentSettings = Field(default_factory=AgentSettings)
    """
    The settings the agent reads.
    """

    checkpoint_steps: PositiveInt = 250_000
    """
    The environment steps between checkpoints. A training run writes each
    at the first episode end, or the end of a rollout's update for PQN and
    PPO, reaching a multiple of them, and a search at the first iteration
    end reaching one. The default is the 250,000 steps of each iteration
    Dopamine's DQN checkpoints after.
    """

    curriculum: CurriculumSettings = Field(default_factory=CurriculumSettings)
    """
    The settings of the curriculum starting each training episode along a
    demonstration.
    """

    emulator: EmulatorSettings = Field(default_factory=EmulatorSettings)
    """
    The settings the emulator reads.
    """

    environment: EnvironmentSettings = Field(default_factory=EnvironmentSettings)
    """
    The settings the environment reads.
    """

    evaluation: EvaluationSettings = Field(default_factory=EvaluationSettings)
    """
    The settings each evaluation of the agent reads.
    """

    evaluation_steps: PositiveInt = 250_000
    """
    The environment steps between the evaluations a run plays, each where
    an episode end, the end of a rollout's update for PQN and PPO, or the
    run's last step first reaches a multiple of them, whose default is the
    250,000 steps of each iteration Dopamine's DQN evaluates after.
    """

    reward: RewardSettings = Field(default_factory=RewardSettings)
    """
    The settings the reward reads.
    """

    search: SearchSettings = Field(default_factory=SearchSettings)
    """
    The settings a search reads.
    """

    seed: NonNegativeInt = 1
    """
    The seed every random draw in the run derives from, whose default
    follows CleanRL's `dqn_atari.py`.
    """

    steps: PositiveInt = 2_500_000
    """
    The environment steps the run takes, a run of PQN or PPO going on to
    the end of the rollout that reaches them, whose default is ten of the
    250,000-step iterations Dopamine's DQN evaluates after.
    """

    @property
    def seeds(self) -> dict[Stream, int]:
        """
        Spawns one child of a `SeedSequence` over `seed` for each stream,
        in the order `Stream` declares its members, and draws each child's
        seed.

        Returns:
            Each stream's seed, a 64-bit unsigned integer, which
            `torch.manual_seed` and Gymnasium's `reset` both take.
        """
        return {
            stream: child.generate_state(1, uint64).item()
            for stream, child in zip(Stream, SeedSequence(self.seed).spawn(len(Stream)))
        }

    @model_validator(mode="after")
    def verify(self) -> Self:
        """
        Refuses a demonstration for the deep Q-network, whose episodes start
        in Blue's bedroom alone, and reward settings whose ceiling at the
        environment's goal passes 1, the bound Mnih et al. clip each reward
        to.

        Raises:
            ValueError: Where either holds, which Pydantic raises as a
                        `ValidationError`.
        """
        if self.curriculum.demonstration and self.agent.algorithm is Algorithm.DQN:
            raise ValueError(
                f"the deep Q-network starts every episode in Blue's bedroom, so it "
                f"takes no demonstration such as {self.curriculum.demonstration}"
            )

        if (ceiling := self.reward.ceiling(goal := self.environment.goal)) > 1:
            raise ValueError(
                f"a step reaching a new position and every flag up to {goal.name} "
                f"at once earns {ceiling - 1:.3g} more than the 1 Mnih et al. clip "
                f"each reward to"
            )

        return self


class SearchRunSettings(RunSettings):
    """
    The settings `squirtl search` reads, `RunSettings` with the curriculum,
    the evaluations, and the steps between them taking no flag, so the
    command parses and lists none of the settings only training reads and
    records their defaults.
    """

    curriculum: Annotated[CurriculumSettings, Parameter(parse=False)] = Field(
        default_factory = CurriculumSettings
    )
    """
    The settings of the curriculum, at their defaults.
    """

    evaluation: Annotated[EvaluationSettings, Parameter(parse=False)] = Field(
        default_factory = EvaluationSettings
    )
    """
    The settings each evaluation reads, at their defaults.
    """

    evaluation_steps: Annotated[PositiveInt, Parameter(parse=False)] = (
        RunSettings.model_fields["evaluation_steps"].default
    )
    """
    The environment steps between evaluations, at their default.
    """


class TrainingSettings(RunSettings):
    """
    The settings `squirtl train` reads, `RunSettings` with `search` taking
    no flag, so the command parses and lists none of a search's settings and
    records their defaults.
    """

    search: Annotated[SearchSettings, Parameter(parse=False)] = Field(
        default_factory = SearchSettings
    )
    """
    The settings a search reads, at their defaults.
    """
