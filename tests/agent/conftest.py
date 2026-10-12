"""
Defines the fixtures the tests of `squirtl.agent` request:

- `space`, the observation space the environment declares
- `build`, a factory building an agent on the CPU over it
- `stacked`, a function stacking each entry of an episode's observations as
  a frame stack does
- `episode` and `observation`, random episodes and one random observation of
  that space
- `play`, a function playing an episode through an agent
- `resume`, a function restoring an agent's checkpoint into another
"""

from collections.abc  import Callable, Mapping
from gymnasium.spaces import Box, Dict
from itertools        import pairwise
from numpy            import arange, ndarray, pad, uint8
from numpy.random     import default_rng
from pathlib          import Path
from pytest           import fixture

from squirtl.agent.learner import Agent
from squirtl.agent.schemas import AgentSettings, Checkpoint

type Observations = list[dict[str, ndarray]]


@fixture
def build(space: Dict) -> Callable[..., Agent]:
    """
    Builds a factory of agents for seven actions over `space`, on the CPU,
    where a training step is pinned, from seed 1 for a run of 1,000 steps
    unless the call names another seed or run length, with any other keyword
    setting a field of its settings.
    """

    def build(seed: int = 1, steps: int = 1000, **settings: object) -> Agent:
        """
        Builds the agent `seed` and `steps` describe, its settings the
        defaults on the CPU with `settings` applied over them.
        """
        return Agent(
            actions  = 7,
            seed     = seed,
            settings = AgentSettings(device="cpu", **settings),
            space    = space,
            steps    = steps
        )

    return build


@fixture
def episode(
    space   : Dict,
    stacked : Callable[[Mapping[str, ndarray], Dict], Observations]
) -> Callable[[int], Observations]:
    """
    Builds a function drawing the `steps + 1` observations of one episode
    of random elements of `space`, the reset observation first, from a
    generator seeded at 0, so each call draws another episode.
    """
    rng = default_rng(0)

    def episode(steps: int) -> Observations:
        """
        Draws the episode's elements for every entry and stacks them.
        """
        return stacked(
            {
                key: rng.integers(
                    entry.high.max(),
                    dtype    = uint8,
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
    an agent, each step taking the action the agent chooses, reaching the
    next observation, earning a reward of one, and stored as terminating the
    episode wherever `terminated` is set, with no update taken.
    """

    def play(agent: Agent, steps: int, terminated: bool = False):
        """
        Plays those steps through `agent`, as the fixture describes.
        """
        observations = episode(steps)
        agent.begin(observations[0])

        for observation, reached in pairwise(observations):
            agent.remember(agent.act(observation), reached, 1.0, terminated)

    return play


@fixture
def resume(build: Callable[..., Agent], tmp_path: Path) -> Callable[[Agent], Agent]:
    """
    Builds a function saving an agent's checkpoint under `tmp_path` and
    restoring it into an agent built from seed 2.
    """

    def resume(agent: Agent) -> Agent:
        """
        Saves `agent`'s checkpoint and restores it into the new agent.

        Returns:
            The agent the checkpoint was restored into.
        """
        agent.checkpoint.save(tmp_path / "checkpoint.pt")
        restored = build(seed=2)
        restored.restore(Checkpoint.from_path(tmp_path / "checkpoint.pt"))

        return restored

    return resume


@fixture
def space() -> Dict:
    """
    Declares the observation the environment makes, each entry stacked along
    its first axis, meaning four stacked 72 by 80 frames beside a 48 by 48
    grid and four flags that each stack one deep.
    """
    return Dict(
        flags  = Box(0, 1, (1, 4), uint8),
        frames = Box(0, 255, (4, 72, 80), uint8),
        grid   = Box(0, 1, (1, 48, 48), uint8)
    )


@fixture
def stacked() -> Callable[[Mapping[str, ndarray], Dict], Observations]:
    """
    Builds a function stacking an episode's elements, the reset element of
    each entry first, into one observation per element. Each entry stacks as
    deep as the space the function is given declares, padded as Gymnasium's
    `FrameStackObservation` pads under its default `reset` padding, which
    repeats the first element.
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
