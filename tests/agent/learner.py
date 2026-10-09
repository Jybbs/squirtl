"""
Pins the agent, each training step on the CPU under a fixed seed, covering:

- An update changing the online network and leaving the target alone, no
  update until replay memory holds a batch, the target each update moves
  toward, and the norm it clips the gradient to
- The target network copying the online network every `sync_steps` steps
- The chance of a random action across the run, the random actions it
  draws, and the greedy action it evaluates with no autograd graph
- The weights a seed builds, which leave each of torch's global generators
  alone
- A restored checkpoint training and drawing as the saved agent would
"""

from collections.abc     import Callable
from copy                import deepcopy
from numpy               import ndarray
from pytest              import MonkeyPatch, approx, mark, param
from torch               import allclose, as_tensor, equal, full, get_rng_state, is_inference_mode_enabled, manual_seed
from torch               import no_grad, ones_like
from torch.nn.functional import huber_loss
from torch.nn.utils      import parameters_to_vector

from squirtl.agent.learner import Agent


def test_a_greedy_action_is_the_one_the_online_network_values_highest(
    build       : Callable[..., Agent],
    observation : ndarray
):
    """
    Asserts that at a chance of zero the agent chooses the action the online
    network values highest, evaluating it with autograd recording nothing,
    under `torch.inference_mode`.
    """
    agent = build(epsilon_end=0, epsilon_start=0)
    modes = []

    with no_grad():
        values = agent.online(as_tensor(observation)[None])

    agent.online.register_forward_hook(
        lambda *_: modes.append(is_inference_mode_enabled())
    )

    assert agent.act(observation) == values.argmax().item()
    assert modes == [True]


@mark.parametrize(
    ("steps", "moved"),
    [
        param(31, False, id="a-transition-short-of-a-batch"),
        param(32, True, id="a-full-batch")
    ]
)
def test_an_update_waits_for_replay_to_hold_a_batch(
    build : Callable[..., Agent],
    moved : bool,
    play  : Callable[..., None],
    steps : int
):
    """
    Asserts that an update leaves the online network as it was while replay
    memory holds fewer transitions than `batch_size`, and moves it once
    replay holds that many.
    """
    agent = build()
    play(agent, steps)
    online = parameters_to_vector(agent.online.parameters())

    agent.update()

    assert (not equal(parameters_to_vector(agent.online.parameters()), online)) is moved


@mark.parametrize(
    ("terminated", "target"),
    [
        param(False, 1.5,  id="a-step-the-episode-goes-on-from"),
        param(True,  1.0,  id="a-terminated-step")
    ]
)
def test_an_update_targets_each_reward_plus_the_discounted_value_that_follows(
    build       : Callable[..., Agent],
    monkeypatch : MonkeyPatch,
    play        : Callable[..., None],
    target      : float,
    terminated  : bool
):
    """
    Asserts that an update draws a batch of `batch_size` and moves each
    value toward its reward of one plus `discount` times the highest value
    the target network gives the observation reached, which a target network
    whose last layer has zero weights and a bias of one puts at one, so
    1.5 for a batch of 8 at a discount of 0.5, and toward the reward of one
    alone where the step terminated the episode.
    """
    agent   = build(batch_size=8, discount=0.5)
    targets = []

    with no_grad():
        agent.target[-1].weight.zero_()
        agent.target[-1].bias.fill_(1)

    play(agent, 8, terminated)
    monkeypatch.setattr(
        "squirtl.agent.learner.huber_loss",
        lambda values, given: targets.append(given) or huber_loss(values, given)
    )

    agent.update()

    assert allclose(targets[0], full((8,), target))


@mark.parametrize(
    "chance",
    [param(0.0, id="a-greedy-action"), param(1.0, id="a-random-action")]
)
def test_an_action_is_a_python_int(
    build       : Callable[..., Agent],
    chance      : float,
    observation : ndarray
):
    """
    Asserts that the agent chooses each action as a Python `int`, greedy or
    random, the type an environment's `step` takes.
    """
    assert type(build(epsilon_end=chance, epsilon_start=chance).act(observation)) is int


def test_a_random_action_reaches_every_action_the_network_values(
    build       : Callable[..., Agent],
    observation : ndarray
):
    """
    Asserts that at a chance of one the agent draws its actions from its own
    generator, reaching every one of the seven actions, and that two agents
    built from one seed draw the same actions.
    """
    first, second = (
        [agent.act(observation) for _ in range(100)] for agent in (build(), build())
    )

    assert first == second
    assert set(first) == set(range(7))


@mark.parametrize(
    ("steps", "synced"),
    [param(3, False, id="a-step-short-of-the-sync"), param(4, True, id="on-the-sync")]
)
def test_the_target_copies_the_online_network_every_sync_steps(
    build  : Callable[..., Agent],
    play   : Callable[..., None],
    steps  : int,
    synced : bool
):
    """
    Asserts that the target network takes the online network's parameters on
    the step `sync_steps` divides, and not on the step before it, each step
    counted as one transition remembered.
    """
    agent = build(sync_steps=4)

    with no_grad():
        agent.online[-1].bias.add_(1)

    play(agent, steps)

    assert equal(
        parameters_to_vector(agent.online.parameters()),
        parameters_to_vector(agent.target.parameters())
    ) is synced


@mark.parametrize(
    ("fraction", "step", "epsilon"),
    [
        param(0.1, 0,    1.0,   id="the-first-step"),
        param(0.1, 50,   0.505, id="halfway-through-exploration"),
        param(0.1, 100,  0.01,  id="the-end-of-exploration"),
        param(0.1, 1000, 0.01,  id="the-last-step"),
        param(0.5, 250,  0.505, id="halfway-through-half-the-run")
    ]
)
def test_the_chance_of_a_random_action_falls_over_the_exploration_fraction(
    build    : Callable[..., Agent],
    epsilon  : float,
    fraction : float,
    step     : int
):
    """
    Asserts that the chance of a random action falls linearly from 1.0 to
    0.01 over the `exploration_fraction` of a 1,000-step run, its first
    tenth by default, counted in environment steps, and holds at 0.01 after
    it.
    """
    agent      = build(exploration_fraction=fraction)
    agent.step = step

    assert agent.epsilon == approx(epsilon)


def test_a_restored_agent_draws_what_the_saved_agent_would(
    build  : Callable[..., Agent],
    play   : Callable[..., None],
    resume : Callable[[Agent], Agent]
):
    """
    Asserts that an agent restoring a checkpoint continues both of the saved
    agent's generators, choosing the random actions it would choose and
    drawing the slots replay memory would draw.
    """
    saved = build()
    play(saved, 5)

    first, second = (
        (agent.exploration.random(), agent.replay.generator.random())
        for agent in (saved, resume(saved))
    )

    assert first == second


def test_a_restored_agent_keeps_training_from_the_saved_state(
    build  : Callable[..., Agent],
    play   : Callable[..., None],
    resume : Callable[[Agent], Agent]
):
    """
    Asserts that an agent restoring a checkpoint takes the saved agent's
    networks and step count, and that its next update moves its own
    online network, Adam counting that update after the saved ones, so the
    optimizer steps the parameters the checkpoint loaded into.
    """
    saved = build()
    play(saved, 33)
    saved.update()
    saved.update()
    restored = resume(saved)

    assert restored.step == saved.step
    assert all(
        equal(
            parameters_to_vector(mine.parameters()),
            parameters_to_vector(theirs.parameters())
        )
        for mine, theirs in (
            (restored.online, saved.online),
            (restored.target, saved.target)
        )
    )

    play(restored, 32)
    online = parameters_to_vector(restored.online.parameters())
    restored.update()

    assert not equal(parameters_to_vector(restored.online.parameters()), online)
    assert {state["step"].item() for state in restored.optimizer.state.values()} == {3}


@mark.parametrize(
    ("seed", "same"),
    [param(1, True, id="the-same-seed"), param(2, False, id="another-seed")]
)
def test_a_seed_builds_the_online_networks_weights(
    build : Callable[..., Agent],
    same  : bool,
    seed  : int
):
    """
    Asserts that agents built from one seed start from the same weights, and
    from different weights under different seeds, with the target network
    starting as a copy of the online network.
    """
    first, second = build(seed=1), build(seed=seed)

    assert equal(
        parameters_to_vector(first.online.parameters()),
        parameters_to_vector(second.online.parameters())
    ) is same
    assert equal(
        parameters_to_vector(second.online.parameters()),
        parameters_to_vector(second.target.parameters())
    )


def test_an_update_changes_the_online_network_and_leaves_the_target_alone(
    build : Callable[..., Agent],
    play  : Callable[..., None]
):
    """
    Asserts that one update on a batch drawn from replay memory moves the
    online network's parameters and leaves every parameter of the target
    network as it was.
    """
    agent = build()
    play(agent, 32)
    online, target = (
        parameters_to_vector(network.parameters()) for network in (
            agent.online, agent.target
        )
    )

    agent.update()

    assert not equal(parameters_to_vector(agent.online.parameters()), online)
    assert equal(parameters_to_vector(agent.target.parameters()), target)


def test_an_update_clips_the_gradient_norm_at_max_grad_norm(
    build : Callable[..., Agent],
    play  : Callable[..., None]
):
    """
    Asserts that the gradient Adam steps on carries a norm of
    `max_grad_norm`, read through a hook that runs before the step.
    """
    agent = build(max_grad_norm=1e-3)
    norms = []
    play(agent, 32)
    agent.optimizer.register_step_pre_hook(
        lambda *_: norms.append(
            parameters_to_vector(
                parameter.grad for parameter in agent.online.parameters()
            ).norm().item()
        )
    )

    agent.update()

    assert norms == [approx(1e-3, rel=1e-4)]


def test_an_update_computes_its_gradient_afresh(
    build : Callable[..., Agent],
    play  : Callable[..., None]
):
    """
    Asserts that an update leaves each parameter holding the gradient of its
    own batch alone, whatever gradient the parameter held before it.
    """
    agent = build()
    play(agent, 32)
    twin = deepcopy(agent)

    for parameter in agent.online.parameters():
        parameter.grad = ones_like(parameter)

    agent.update()
    twin.update()

    assert equal(
        parameters_to_vector(parameter.grad for parameter in agent.online.parameters()),
        parameters_to_vector(parameter.grad for parameter in twin.online.parameters())
    )


@mark.parametrize(
    ("setting", "value", "read"),
    [
        param(
            "capacity",
            64,
            lambda agent: len(agent.replay.frames),
            id = "the-frames-replay-memory-holds"
        ),
        param(
            "learning_rate",
            3e-4,
            lambda agent: agent.optimizer.param_groups[0]["lr"],
            id = "adams-learning-rate"
        )
    ]
)
def test_the_agent_builds_on_the_settings_it_is_given(
    build   : Callable[..., Agent],
    read    : Callable[[Agent], object],
    setting : str,
    value   : object
):
    """
    Asserts that the agent sizes replay memory and sets Adam's learning rate
    from the settings it is built with rather than from any default.
    """
    assert read(build(**{setting: value})) == value


@mark.parametrize(
    "reseed",
    [
        param("torch.cuda.manual_seed_all", id="cuda"),
        param("torch.mps.manual_seed",      id="mps")
    ]
)
def test_building_an_agent_reseeds_no_accelerators_generator(
    build       : Callable[..., Agent],
    monkeypatch : MonkeyPatch,
    reseed      : str
):
    """
    Asserts that building an agent reseeds no accelerator's global
    generator, which the fork of the CPU generator its weights draw from
    leaves unrestored.
    """
    reseeded = []
    monkeypatch.setattr(reseed, reseeded.append)

    build()

    assert reseeded == []


def test_building_an_agent_leaves_torchs_global_generator_alone(
    build: Callable[..., Agent]
):
    """
    Asserts that building an agent leaves the state of torch's global CPU
    generator as it found it, since the weights draw from a fork of it.
    """
    manual_seed(5)
    build()

    assert equal(get_rng_state(), manual_seed(5).get_state())
