"""
Defines the fixtures the tests of `squirtl.agent` request, meaning a factory
building an agent on the CPU, a function stacking an episode's frames as
a frame stack does, one random observation, a function playing an episode
through an agent, and a function restoring an agent's checkpoint into
another.
"""

from collections.abc import Callable
from itertools       import pairwise
from numpy           import arange, ndarray, pad, uint8
from numpy.random    import default_rng
from pathlib         import Path
from pytest          import fixture

from squirtl.agent.learner import Agent
from squirtl.agent.schemas import AgentSettings, Checkpoint


@fixture
def build() -> Callable[..., Agent]:
    """
    Builds a factory of agents for seven actions over four stacked 72 by
    80 frames, on the CPU, where a training step is pinned, from seed 1 for
    a run of 1,000 steps unless the call names another seed or run length,
    with any other keyword setting a field of its settings.
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
            shape    = (4, 72, 80),
            steps    = steps
        )

    return build


@fixture
def episode() -> Callable[[ndarray], list[ndarray]]:
    """
    Builds a function stacking an episode's frames four deep as Gymnasium's
    `FrameStackObservation` does under its default `reset` padding, which
    repeats the first frame.
    """

    def episode(frames: ndarray) -> list[ndarray]:
        """
        Stacks `frames`, the reset frame first, into one observation per
        frame, each ending on that frame.
        """
        return list(
            pad(frames, ((3, 0), (0, 0), (0, 0)), mode="edge")[
                arange(len(frames))[:, None] + arange(4)
            ]
        )

    return episode


@fixture
def observation() -> ndarray:
    """
    Draws one stack of four random 72 by 80 `uint8` frames from seed 0.
    """
    return default_rng(0).integers(256, dtype=uint8, size=(4, 72, 80))


@fixture
def play(episode: Callable[[ndarray], list[ndarray]]) -> Callable[..., None]:
    """
    Builds a function playing `steps` steps of one episode of random
    frames through an agent, each step taking the action the agent chooses,
    reaching the next frame, earning a reward of one, and stored as
    terminating the episode wherever `terminated` is set, with no update
    taken.
    """
    rng = default_rng(0)

    def play(agent: Agent, steps: int, terminated: bool = False):
        """
        Plays those steps through `agent`, as the fixture describes.
        """
        observations = episode(rng.integers(256, dtype=uint8, size=(steps + 1, 72, 80)))
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
