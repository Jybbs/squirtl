"""
Defines the fixtures the tests of `squirtl.agent` request:

- `space`, the observation space the environment declares
- `build`, agents over that space on the CPU
- `episode`, `observation`, and `stacked`, random episodes and observations
  of that space, stacked as a frame stack stacks them
- `play` and `resume`, which play an episode through an agent and restore
  its checkpoint into another built under the same settings
- `rolling`, `batched`, and `collect`, PQN and PPO over that space, a batch
  of its observations, and a function filling such an agent's rollout
"""

from collections.abc        import Callable, Mapping
from gymnasium.spaces       import Box, Dict, MultiBinary, flatten_space
from gymnasium.vector.utils import batch_space
from itertools              import pairwise
from numpy        import arange, float32, full, ndarray, pad, uint8, zeros
from numpy.random import default_rng
from pathlib      import Path
from pytest       import fixture

from squirtl.agent.learner       import DQN, RolloutAgent
from squirtl.agent.schemas       import AgentSettings, Algorithm, ReplayCheckpoint
from squirtl.environment.schemas import Entry

type Observations = list[dict[str, ndarray]]


@fixture
def batched(space: Dict) -> dict[str, ndarray]:
    """
    Samples one observation of `space` for each of two environments, from
    seed 0.
    """
    batch = batch_space(space, 2)
    batch.seed(0)

    return batch.sample()


@fixture
def build(space: Dict) -> Callable[..., DQN]:
    """
    Builds a factory of agents for seven actions over `space` on the CPU,
    from seed 1 for a 1,000-step run unless the call names another seed or
    length, any other keyword setting a field of its settings.
    """

    def build(seed: int = 1, steps: int = 1000, **settings: object) -> DQN:
        """
        Builds the agent `seed` and `steps` describe, its settings the
        defaults on the CPU with `settings` applied over them.
        """
        return DQN(
            actions  = 7,
            seed     = seed,
            settings = AgentSettings(device="cpu", **settings),
            space    = space,
            steps    = steps
        )

    return build


@fixture
def collect(batched: dict[str, ndarray]) -> Callable[[RolloutAgent], None]:
    """
    Builds a function filling an agent's rollout from `batched`, each step
    earning each environment a reward of one and ending no episode.
    """

    def collect(agent: RolloutAgent):
        """
        Takes a rollout's steps through `agent`, as the fixture describes.
        """
        for _ in range(agent.settings.hyperparameters.rollout_steps):
            agent.act(batched)
            agent.remember(
                bootstraps = zeros(2, float32),
                rewards    = full(2, 1.0, float32),
                terminated = zeros(2, bool),
                truncated  = zeros(2, bool)
            )

    return collect


@fixture
def episode(
    space   : Dict,
    stacked : Callable[[Mapping[str, ndarray], Dict], Observations]
) -> Callable[[int], Observations]:
    """
    Builds a function drawing the `steps + 1` observations of one random
    episode of `space`, the reset first, from a generator seeded at 0, so
    each call draws another.
    """
    rng = default_rng(0)

    def episode(steps: int) -> Observations:
        """
        Draws the episode's elements for every entry and stacks them.
        """
        return stacked(
            {
                key: rng.integers(
                    flatten_space(entry).high.max(),
                    dtype    = entry.dtype,
                    endpoint = True,
                    size     = (steps + 1, *entry.shape[1:])
                )
                for key, entry in space.items()
            },
            space
        )

    return episode


@fixture
def observation(space: Dict) -> dict[str, ndarray]:
    """
    Samples one observation of `space` from seed 0.
    """
    space.seed(0)

    return space.sample()


@fixture
def play(episode: Callable[[int], Observations]) -> Callable[..., None]:
    """
    Builds a function playing `steps` steps of one random episode through
    an agent, each taking the agent's action, earning a reward of one, and
    stored as terminating wherever `terminated` is set, with no update.
    """

    def play(agent: DQN, steps: int, terminated: bool = False):
        """
        Plays those steps through `agent`, as the fixture describes.
        """
        observations = episode(steps)
        agent.begin(observations[0])

        for observation, reached in pairwise(observations):
            agent.remember(agent.act(observation), reached, 1.0, terminated)

    return play


@fixture
def resume(space: Dict, tmp_path: Path) -> Callable[[DQN], DQN]:
    """
    Builds a function saving an agent's checkpoint under `tmp_path` and
    restoring it into an agent built from seed 2 under the saved agent's
    settings and run length, as a resumed run builds its agent under the
    settings its run recorded.
    """

    def resume(agent: DQN) -> DQN:
        """
        Saves `agent`'s checkpoint and restores it into the new agent.

        Returns:
            The agent the checkpoint was restored into.
        """
        agent.checkpoint.save(tmp_path / "checkpoint.npz")
        restored = DQN(
            actions  = agent.actions,
            seed     = 2,
            settings = agent.settings,
            space    = space,
            steps    = agent.steps
        )
        restored.restore(ReplayCheckpoint.from_path(tmp_path / "checkpoint.npz"))

        return restored

    return resume


@fixture
def rolling(space: Dict) -> Callable[..., RolloutAgent]:
    """
    Builds a factory of PQN and PPO agents for seven actions over `space` on
    the CPU, each splitting rollouts of four steps across two environments
    into two minibatches, from seed 1 for a 1,000-step run unless the call
    names another seed, length, or count of minibatches, any other keyword
    setting a field of the agent's own settings.
    """

    def rolling(
        algorithm   : Algorithm,
        minibatches : int = 2,
        seed        : int = 1,
        steps       : int = 1000,
        **fields    : object
    ) -> RolloutAgent:
        """
        Builds the agent of `algorithm` the arguments describe.
        """
        return RolloutAgent.named(algorithm)(
            actions      = 7,
            environments = 2,
            seed         = seed,
            settings     = AgentSettings(
                **{
                    algorithm.value: {
                        "minibatches"   : minibatches,
                        "rollout_steps" : 4,
                        **fields
                    }
                },
                algorithm    = algorithm,
                device       = "cpu",
                environments = 2
            ),
            space = space,
            steps = steps
        )

    return rolling


@fixture
def space() -> Dict:
    """
    Declares the environment's observation, four stacked 72 by 80 frames
    beside a binary 48 by 48 grid and four binary flags, those two one deep.
    """
    return Dict(
        {
            Entry.FLAGS  : MultiBinary((1, 4)),
            Entry.FRAMES : Box(0, 255, (4, 72, 80), uint8),
            Entry.GRID   : MultiBinary((1, 48, 48))
        }
    )


@fixture
def stacked() -> Callable[[Mapping[str, ndarray], Dict], Observations]:
    """
    Builds a function stacking an episode's elements, the reset first, into
    one observation each, every entry as deep as its space and padded with
    its first element, as `FrameStackObservation` pads by default.
    """

    def stacked(elements: Mapping[str, ndarray], space: Dict) -> Observations:
        """
        Stacks `elements`, one array per entry, into the observations.
        """
        stacks = {
            key: pad(
                values,
                ((depth - 1, 0), *[(0, 0)] * (values.ndim - 1)),
                mode = "edge"
            )[arange(len(values))[:, None] + arange(depth)]
            for key, values in elements.items()
            for depth in [space[key].shape[0]]
        }

        return [dict(zip(stacks, step)) for step in zip(*stacks.values(), strict=True)]

    return stacked
