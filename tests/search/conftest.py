"""
Defines the fixtures the tests of `squirtl.search` request, `small`, the
settings of a small search, `space`, the frame stacks it reads, `novelty`,
its predictor on the CPU, `specification`, the environment a worker makes,
`booted`, that environment made as a worker makes it, `root`, its reset
state, `playing`, which plays a rollout through it, `rolled` and `rolling`,
which build the `roll` of a search, and `searching`, a factory of searches.
"""

from collections.abc import Callable, Iterable, Iterator
from common.search   import boot_in_place, snapshot
from functools       import partial
from gymnasium       import Env
from gymnasium.envs.registration import EnvSpec
from gymnasium.spaces            import Box
from numpy        import uint8
from numpy.random import default_rng
from pytest       import fixture

from squirtl.agent.schemas         import AgentSettings
from squirtl.emulator.schemas      import Cartridge, EmulatorSettings
from squirtl.environment.overworld import Overworld
from squirtl.environment.schemas   import EnvironmentSettings, Snapshot
from squirtl.reward.schemas        import Event, RewardSettings
from squirtl.search                import workers
from squirtl.search.novelty        import Novelty
from squirtl.search.particles      import Search
from squirtl.search.schemas        import Ending, SearchRollout, SearchSettings
from squirtl.search.workers        import roll


@fixture
def small() -> SearchSettings:
    """
    Builds the settings of a search of two groups of two particles, each
    rollout 2 to 4 presses, each group 1 to 2 outer steps an iteration, an
    update of the predictor every 8 presses drawing 4 stacks from 64 slots,
    and one worker.
    """
    return SearchSettings(
        batch_size   = 4,
        capacity     = 64,
        groups       = 2,
        inner_steps  = (2, 4),
        outer_steps  = (1, 2),
        particles    = 2,
        update_steps = 8,
        workers      = 1
    )


@fixture
def space() -> Box:
    """
    Builds the frame stacks of the environment's default settings.
    """
    return Box(0, 255, (4, 72, 80), uint8)


@fixture
def novelty(small: SearchSettings, space: Box) -> Novelty:
    """
    Builds the predictor of `small` on the CPU from seed 7, its batches
    drawn from a generator seeded at 7.
    """
    return Novelty(AgentSettings(device="cpu"), default_rng(7), 7, small, space)


@fixture
def specification(cartridge: Cartridge) -> EnvSpec:
    """
    Builds the spec of the environment on `cartridge` under the default
    settings, as `RunSettings.specification` builds it.
    """
    return Overworld.specification(
        cartridge,
        EmulatorSettings(),
        EnvironmentSettings(),
        RewardSettings()
    )


@fixture
def booted(specification: EnvSpec) -> Iterator[Env]:
    """
    Runs `boot` on `specification`, putting back the handler of the
    interrupt signal it replaces and closing the environment it makes with
    the test.

    Yields:
        The environment, reset at seed 0 and stepped with no press past the
        logo the boot ROM scrolls, so its screen no longer changes.
    """
    boot_in_place(specification)

    with workers.environment as environment:
        environment.reset(seed=0)

        for _ in range(4):
            environment.step(0)

        yield environment


@fixture
def root(booted: Env) -> Snapshot:
    """
    Captures the environment `booted` makes at its reset.
    """
    return booted.get_wrapper_attr("capture")()


@fixture
def playing(root: Snapshot) -> Callable[..., Ending]:
    """
    Builds a function playing the presses it is handed from `root`, any
    keyword a field of `SearchRollout` to set in its place.
    """

    def play(presses: bytes, **fields: object) -> Ending:
        """
        Plays `presses` as the rollout `fields` describe.
        """
        return roll(SearchRollout(presses=presses, **{"snapshot": root, **fields}))

    return play


@fixture
def searching(small: SearchSettings, space: Box) -> Callable[..., Search]:
    """
    Builds a factory of searches of `small` on the CPU from seed 7 toward
    `EVENT_GOT_STARTER`, starting on an empty `snapshot`, seven actions, a
    `steps` of 10,000, and a `roll` each test hands it, any other keyword a
    field of `SearchSettings`.
    """

    def build(
        roll     : Callable[[Iterable[SearchRollout]], Iterable[Ending]],
        goal     : Event    = Event.EVENT_GOT_STARTER,
        root     : Snapshot = snapshot(),
        seed     : int      = 7,
        steps    : int      = 10_000,
        **fields : object
    ) -> Search:
        """
        Builds the search `fields` describe.
        """
        return Search(
            actions  = 7,
            agent    = AgentSettings(device="cpu"),
            goal     = goal,
            roll     = roll,
            root     = root,
            seed     = seed,
            settings = small.model_copy(update=fields),
            space    = space,
            steps    = steps
        )

    return build


@fixture
def rolled() -> Callable[..., Callable[[Iterable[SearchRollout]], Iterable[Ending]]]:
    """
    Builds a function turning a list of endings into a `roll` that returns
    them in turn and records each rollout it receives.
    """

    def script(
        endings : Iterable[Ending],
        played  : list[SearchRollout] | None = None
    ) -> Callable[[Iterable[SearchRollout]], Iterator[Ending]]:
        """
        Builds the `roll` returning `endings`, appending to `played`.
        """
        remaining = iter(endings)

        def play(rollouts: Iterable[SearchRollout]) -> Iterator[Ending]:
            """
            Records `rollouts` and returns one ending for each.
            """
            for rollout in rollouts:
                if played is not None:
                    played.append(rollout)

                yield next(remaining)

        return play

    return script


@fixture
def rolling(booted: Env) -> Callable[[Iterable[SearchRollout]], Iterable[Ending]]:
    """
    Builds the `roll` of a search playing every rollout on `booted` in the
    process running the test.
    """
    return partial(map, roll)
