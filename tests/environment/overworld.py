"""
Pins how `Overworld` keeps Gymnasium's environment contract, covering:

- `check_env` on the unwrapped environment, which imports nothing from the
  agent, and the intro, the presses, the frames, and the close it makes
- The DIV each reset draws, its idle frame, and the progress it restarts
- Each step's reward, termination, and shares, and the truncation and the
  statistics each episode records
- The wrappers, spaces, grid, flags, render, and render rate it is made
  with, and an agent learning from its observations
"""

from collections.abc  import Callable
from common.console   import set_event, stand
from gymnasium        import Env, make
from gymnasium.spaces import Box, Discrete
from gymnasium.utils.env_checker import check_env
from numpy          import argwhere, uint8
from numpy.random   import default_rng
from numpy.testing  import assert_array_equal
from pytest         import approx, mark, param
from subprocess     import check_output
from sys            import executable
from torch          import equal
from torch.nn.utils import parameters_to_vector

from squirtl.agent.learner         import Agent
from squirtl.agent.schemas         import AgentSettings
from squirtl.emulator.schemas      import Button
from squirtl.environment.overworld import Overworld
from squirtl.environment.schemas   import Entry
from squirtl.reward.schemas        import Event, Position, RewardSettings, Term


def test_a_build_plays_the_intro_before_any_reset(overworld: Overworld):
    """
    Asserts that building the environment plays the intro once at a
    `timer_div` of 0 and resets nothing, its one other call the read of the
    screen that sizes its observation space.
    """
    assert overworld.game_boy.emulator.calls == [("start_game", 0), ("screen",)]


def test_a_close_stops_the_emulator_without_saving(overworld: Overworld):
    """
    Asserts that closing the environment stops the emulator with no save.
    """
    overworld.close()

    assert overworld.game_boy.emulator.calls[-1] == ("stop", False)


def test_a_reset_starts_the_progress_afresh(overworld: Overworld):
    """
    Asserts that a position an earlier episode reached earns novelty again
    in the episode after a reset, since each reset starts its own progress.
    """
    memory  = overworld.game_boy.emulator.memory
    rewards = []

    for _ in range(2):
        stand(memory, Position(map=0, x=0, y=0))
        overworld.reset(seed=0)
        stand(memory, Position(map=0, x=1, y=0))
        rewards.append(overworld.step(0)[1])

    assert rewards == [0.0625, 0.0625]


def test_an_agent_learns_from_the_observations_the_environment_makes(
    made: Callable[..., Env]
):
    """
    Asserts that an agent built over the environment's own spaces stores
    each observation its steps reach and takes an update on a batch of them
    that changes its online network.
    """
    env   = made()
    agent = Agent(
        actions  = env.action_space.n,
        seed     = 0,
        settings = AgentSettings(batch_size=4, capacity=64, device="cpu"),
        space    = env.observation_space,
        steps    = 8
    )
    observation, _ = env.reset(seed=0)
    agent.begin(observation)

    for _ in range(8):
        action = agent.act(observation)
        observation, reward, terminated, _, _ = env.step(action)
        agent.remember(action, observation, reward, terminated)

    online = parameters_to_vector(agent.online.parameters())
    agent.update()

    assert not equal(parameters_to_vector(agent.online.parameters()), online)


@mark.parametrize(
    ("action", "pressed"),
    [
        param(0, [], id="no-press"),
        *(
            param(action, [("button", button, 3)], id=button)
            for action, button in enumerate(Button, start=1)
        )
    ]
)
def test_each_action_makes_its_press_then_advances_the_steps_frames(
    action    : int,
    overworld : Overworld,
    pressed   : list[tuple[str, Button, int]]
):
    """
    Asserts that action 0 presses nothing and action `n` the `n`th `Button`
    as declared, held for `hold`, before one tick of `frames_per_step`
    frames and the read of the screen it ends on.
    """
    overworld.reset(seed=0)
    overworld.game_boy.emulator.calls.clear()
    overworld.step(action)

    assert overworld.game_boy.emulator.calls == [*pressed, ("tick", 20), ("screen",)]


def test_resets_with_no_seed_draw_on_from_the_seeded_generator(overworld: Overworld):
    """
    Asserts that resets after a seeded one draw each episode's `timer_div`
    on from the generator that seed started, rather than reseeding it.
    """
    for seed in (5, None, None):
        overworld.reset(seed=seed)

    assert [
        call[1] for call in overworld.game_boy.emulator.calls if call[0] == "reset_game"
    ] == default_rng(5).integers(256, size=3).tolist()


@mark.parametrize("seed", [param(0, id="seed-0"), param(1, id="seed-1")])
def test_a_reset_writes_a_div_its_seed_draws_then_draws_one_idle_frame(
    overworld : Overworld,
    seed      : int
):
    """
    Asserts that a seeded reset hands the game wrapper the first of DIV's
    256 values its seed draws, from the `PCG64` generator Gymnasium and
    `default_rng` both build, then advances one idle frame and reads its
    screen.
    """
    overworld.game_boy.emulator.calls.clear()
    overworld.reset(seed=seed)

    assert overworld.game_boy.emulator.calls == [
        ("reset_game", default_rng(seed).integers(256)),
        ("tick", 1),
        ("screen",)
    ]


def test_the_action_space_offers_no_press_and_each_button(overworld: Overworld):
    """
    Asserts that the action space holds one action for no press and one for
    each `Button`, so no action presses START or SELECT.
    """
    assert overworld.action_space == Discrete(len(Button) + 1)


def test_the_environment_imports_nothing_from_the_agent():
    """
    Asserts that importing the environment's modules in a fresh interpreter
    imports no module of `squirtl.agent`.
    """
    assert "squirtl.agent" not in check_output(
        [
            executable, "-c",
            "import sys, squirtl.environment.overworld; print(*sys.modules)"
        ],
        text = True
    )


@mark.parametrize(
    ("event", "reward", "terminated"),
    [
        param(Event.EVENT_OAK_APPEARED_IN_PALLET, 0.125, False, id="a-milestone"),
        param(Event.EVENT_GOT_STARTER,            0.5,   True,  id="the-starter")
    ]
)
def test_a_step_returns_its_score_and_never_truncates(
    event      : Event,
    overworld  : Overworld,
    reward     : float,
    terminated : bool
):
    """
    Asserts that a step returns the screen it ends on, the reward its score
    totals, whether it found the starter, no truncation, which `TimeLimit`
    reports, and each term's share as its info dict.
    """
    overworld.reset(seed=0)
    set_event(event, overworld.game_boy.emulator.memory)
    screen, earned, ended, truncated, info = overworld.step(0)

    assert_array_equal(screen, overworld.render())
    assert (earned, ended, truncated) == (reward, terminated, False)
    assert info == {term: reward if term is event.term else 0.0 for term in Term}


def test_the_environment_is_made_through_its_spec_with_gymnasiums_wrappers(
    made: Callable[..., Env]
):
    """
    Asserts that the environment's spec names it and every wrapper
    shaping its observation, in the order each wraps the last, and that
    `gymnasium.make` remakes from it an environment of an equal spec.
    """
    spec = made().spec

    assert (
        spec.id, spec.max_episode_steps,
        [wrapper.name for wrapper in spec.additional_wrappers]
    ) == (
        "squirtl/Overworld-v0", 10_240,
        [
            "GrayscaleObservation", "ShrinkObservation", "FrameStackObservation",
            "ProgressObservation", "RecordEpisodeStatistics"
        ]
    )

    with make(spec) as remade:
        assert remade.spec == spec


def test_the_observation_carries_the_grid_and_the_flags_of_the_episodes_progress(
    made: Callable[..., Env]
):
    """
    Asserts that a reset's grid marks the player's square alone, and that a
    step onto a new square setting a milestone's flag observes both squares
    and that flag, paying the novelty and the milestone.
    """
    env        = made()
    started, _ = env.reset(seed=0)
    memory     = env.unwrapped.game_boy.emulator.memory

    stand(memory, Position(map=0, x=1, y=0))
    set_event(Event.EVENT_OAK_APPEARED_IN_PALLET, memory)
    stepped, reward, *_ = env.step(0)

    assert argwhere(started[Entry.GRID][0]).tolist() == [[24, 24]]
    assert argwhere(stepped[Entry.GRID][0]).tolist() == [[24, 23], [24, 24]]
    assert stepped[Entry.FLAGS][0].tolist() == [
        int(event is Event.EVENT_OAK_APPEARED_IN_PALLET) for event in Event
    ]
    assert reward == approx(RewardSettings().milestone + RewardSettings().novelty)


@mark.parametrize(
    ("fields", "shapes"),
    [
        param(
            {},
            {Entry.FLAGS: (1, 4), Entry.FRAMES: (4, 72, 80), Entry.GRID: (1, 48, 48)},
            id = "the-defaults"
        ),
        param(
            {"frame_stack": 2, "grid_size": 9, "frame_shape": (36, 40)},
            {Entry.FLAGS: (1, 4), Entry.FRAMES: (2, 36, 40), Entry.GRID: (1, 9, 9)},
            id = "other-shapes"
        )
    ]
)
def test_the_observation_lies_in_its_space_at_the_shapes_the_settings_name(
    made   : Callable[..., Env],
    fields : dict[str, object],
    shapes : dict[Entry, tuple[int, ...]]
):
    """
    Asserts that each entry takes the shape the settings name, the frames
    `frame_stack` deep at `frame_shape` in the `uint8` `Box` from 0 to
    255, the grid `grid_size` a side, and one flag per `Event`, and that a
    reset's observation lies in the space declared in each entry's dtype,
    which `MultiBinary.contains` leaves unchecked.
    """
    env            = made(**fields)
    observation, _ = env.reset(seed=0)

    assert {key: value.shape for key, value in observation.items()} == shapes
    assert {key: value.dtype for key, value in observation.items()} == {
        key: entry.dtype for key, entry in env.observation_space.items()
    }
    assert env.observation_space.contains(observation)
    assert env.observation_space[Entry.FRAMES] == Box(
        0,
        255,
        shapes[Entry.FRAMES],
        uint8
    )


def test_the_render_is_the_rgb_screen(made: Callable[..., Env]):
    """
    Asserts that the environment made in the `rgb_array` mode its metadata
    declares renders the screen the console shows, a `(144, 160, 3)` array
    of `uint8` holding its RGB channels.
    """
    with make(made().spec, render_mode="rgb_array") as env:
        env.reset(seed=0)
        render = env.render()

        assert (render.shape, render.dtype) == ((144, 160, 3), uint8)
        assert_array_equal(render, env.unwrapped.game_boy.screen)


def test_the_render_rate_is_one_frame_per_step_at_the_consoles_speed(
    made: Callable[..., Env]
):
    """
    Asserts that the environment renders at the steps a Game Boy takes
    a second at its own speed, the 59.7275 frames a second that Pan
    Docs's 4.194304 MHz clock and 70224 dots a frame give, divided by
    `frames_per_step`.
    """
    assert made(frames_per_step=20).metadata["render_fps"] == approx(59.7275 / 20)


def test_the_time_limit_truncates_the_episode_and_records_it(made: Callable[..., Env]):
    """
    Asserts that the environment truncates an episode on its
    `max_episode_steps`-th step and not before, never terminating it, and
    reports its length in the statistics `RecordEpisodeStatistics` adds.
    """
    env = made(max_episode_steps=3)
    env.reset(seed=0)
    steps = [env.step(0) for _ in range(3)]

    assert [(terminated, truncated) for _, _, terminated, truncated, _ in steps] == [
        (False, False),
        (False, False),
        (False, True)
    ]
    assert steps[-1][-1]["episode"]["l"] == 3


def test_the_unwrapped_environment_passes_gymnasiums_checks(made: Callable[..., Env]):
    """
    Asserts that Gymnasium's `check_env` passes on the unwrapped environment
    with every warning it issues raised as an error, covering its spaces,
    a seeded reset's determinism, a step's returns, the RGB render, and a
    second close.
    """
    check_env(made().unwrapped)
