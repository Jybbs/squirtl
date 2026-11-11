"""
Pins the agent, each training step on the CPU under a fixed seed, covering:

- An update changing the online network and leaving the target alone, no
  update before the warm-up ends or on a step the update interval skips,
  the Double DQN target each update moves toward and the target network's
  own highest value in its place, the norm it clips the gradient to, the
  gradient it computes afresh rather than adding to the one a parameter
  held, and the loss and value it returns
- The capacity of replay memory and Adam's learning rate, each read from
  the settings the agent is built with, and the NNPACK flag and the thread
  count it sets for its whole process
- The target network copying the online network every `sync_steps` steps,
  before the update of a step both intervals divide
- The chance of a random action across the run, the random actions it
  draws, and the greedy action it evaluates with no autograd graph
- The weights a seed builds, which leave each of PyTorch's global generators
  alone
- A restored checkpoint training and drawing as the saved agent would,
  replay memory included, and one holding networks of another shape
  refused
- The network and the optimizer PQN and PPO each train with, the actions
  each chooses and stores in its rollout, and what each draws from its own
  generator alone
- Each loss worked by hand, the λ, the discount, and the minibatches an
  update reads, the norm it clips the gradient to, the measures it averages,
  and a restored agent training as the saved agent would
"""

from collections.abc     import Callable, Iterator
from common.agents       import each_agent
from contextlib          import ExitStack
from copy                import deepcopy
from gymnasium.spaces    import Dict, MultiBinary
from math                import exp, log
from numpy               import float32, ndarray
from pathlib             import Path
from pytest              import MonkeyPatch, approx, fixture, mark, param, raises
from torch               import Tensor, arange, as_tensor, equal, full, get_num_threads, get_rng_state
from torch               import is_inference_mode_enabled, manual_seed, no_grad, ones_like, set_num_threads, tensor
from torch               import uint8, zeros
from torch.backends      import nnpack
from torch.nn            import LayerNorm, Linear, Module
from torch.nn.functional import huber_loss, one_hot
from torch.nn.utils      import clip_grad_norm_, parameters_to_vector
from torch.optim         import AdamW, Optimizer, RAdam
from torch.testing       import assert_close

from squirtl.agent.checkpoint    import RolloutCheckpoint
from squirtl.agent.learner       import DQN, RolloutAgent
from squirtl.agent.networks      import ActorCritic, QNetwork
from squirtl.agent.rollout       import Rollout
from squirtl.agent.schemas       import AgentSettings, Algorithm, Measures, PolicyUpdate, Update
from squirtl.environment.schemas import Entry
from squirtl.reward.schemas      import Event


@fixture
def two_threads() -> Iterator[None]:
    """
    Sets the threads PyTorch runs on to two for the test, then back to the
    count it held once the test ends, since an agent sets that count for its
    whole process.
    """
    with ExitStack() as stack:
        stack.callback(set_num_threads, get_num_threads())
        set_num_threads(2)

        yield


def batch_of(**fields: list[float]) -> dict[str, Tensor]:
    """
    Builds a minibatch of two blank observations of the agents' space, with
    a `float32` tensor per field of `fields`, every action the first unless
    `fields` names others.
    """
    return {
        Entry.FLAGS  : zeros((2, 1, 4), dtype=uint8),
        Entry.FRAMES : zeros((2, 4, 72, 80), dtype=uint8),
        Entry.GRID   : zeros((2, 1, 48, 48), dtype=uint8),
        "actions"    : tensor(fields.pop("actions", [0, 0])),
        **{name: tensor(values) for name, values in fields.items()}
    }


@mark.parametrize(
    ("warmup", "interval", "steps", "moved"),
    [
        param(32, 1, 31, False, id="a-step-short-of-the-warmup"),
        param(32, 1, 32, True,  id="the-warmups-last-step"),
        param(33, 4, 35, False, id="a-step-the-interval-skips"),
        param(33, 4, 36, True,  id="a-step-the-interval-divides"),
        param(40, 4, 36, False, id="a-step-the-interval-divides-inside-the-warmup")
    ]
)
def test_an_update_lands_on_each_step_the_interval_divides_once_the_warmup_ends(
    build    : Callable[..., DQN],
    interval : int,
    moved    : bool,
    play     : Callable[..., None],
    steps    : int,
    warmup   : int
):
    """
    Asserts that an update leaves the online network as it was and returns
    `None` before the agent has remembered `warmup_steps` steps or on a step
    `update_steps` does not divide, and moves it and returns what it read on
    a step `update_steps` divides once the agent has remembered that many.
    """
    agent = build(update_steps=interval, warmup_steps=warmup)
    play(agent, steps)
    online = parameters_to_vector(agent.online.parameters())

    assert (
        agent.update() is not None,
        not equal(parameters_to_vector(agent.online.parameters()), online)
    ) == (moved, moved)


@mark.parametrize(
    ("double_q", "terminated", "target"),
    [
        param(True,  False, 2.0, id="the-online-networks-choice"),
        param(False, False, 4.0, id="the-target-networks-own-choice"),
        param(True,  True,  1.0, id="a-terminated-step")
    ]
)
def test_an_update_targets_each_reward_plus_the_discounted_value_that_follows(
    build       : Callable[..., DQN],
    double_q    : bool,
    monkeypatch : MonkeyPatch,
    play        : Callable[..., None],
    target      : float,
    terminated  : bool
):
    """
    Asserts that an update draws a batch of `batch_size` and moves each
    value toward its reward of one plus `discount` times the value the
    target network gives the observation reached under the action the
    online network chooses there, and under the action the target network
    values highest where `double_q` is off. Each network's last layer
    has zero weights, the online network's bias choosing action 2 and the
    target network's valuing each action at its index, so a batch of 8 at a
    discount of 0.5 targets 2.0 and 4.0, and the reward of one alone where
    the step terminated the episode.
    """
    agent = build(
        batch_size   = 8,
        discount     = 0.5,
        double_q     = double_q,
        warmup_steps = 8
    )
    targets = []

    with no_grad():
        for network in (agent.online, agent.target):
            network.head.weight.zero_()

        agent.online.head.bias.copy_(one_hot(tensor(2), 7))
        agent.target.head.bias.copy_(arange(7))

    play(agent, 8, terminated)
    monkeypatch.setattr(
        "squirtl.agent.learner.huber_loss",
        lambda values, given: targets.append(given) or huber_loss(values, given)
    )

    agent.update()

    assert_close(targets[0], full((8,), target))


@mark.parametrize(
    "chance",
    [param(0.0, id="a-greedy-action"), param(1.0, id="a-random-action")]
)
def test_an_action_is_a_python_int(
    build       : Callable[..., DQN],
    chance      : float,
    observation : dict[str, ndarray]
):
    """
    Asserts that the agent chooses each action as a Python `int`, greedy or
    random, the type an environment's `step` takes.
    """
    assert type(build(epsilon_end=chance, epsilon_start=chance).act(observation)) is int


def flat(bias: Tensor | list[float], head: Linear):
    """
    Zeroes the weights of `head` and sets its bias, so it reads that bias
    alone whatever the layer beneath it holds.
    """
    with no_grad():
        head.weight.zero_()
        head.bias.copy_(as_tensor(bias, dtype=head.bias.dtype))


@mark.parametrize(
    ("steps", "synced"),
    [param(3, False, id="a-step-short-of-the-sync"), param(4, True, id="on-the-sync")]
)
def test_the_target_copies_the_online_network_every_sync_steps(
    build  : Callable[..., DQN],
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
        agent.online.head.bias.add_(1)

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
    build    : Callable[..., DQN],
    epsilon  : float,
    fraction : float,
    step     : int
):
    """
    Asserts that the chance of a random action falls linearly from 1.0 to
    0.01 over the `exploration_fraction` of a 1,000-step run, counted in
    environment steps, and holds at 0.01 after it.
    """
    agent      = build(exploration_fraction=fraction)
    agent.step = step

    assert agent.epsilon == approx(epsilon)


def test_a_greedy_action_is_the_one_the_online_network_values_highest(
    build       : Callable[..., DQN],
    observation : dict[str, ndarray]
):
    """
    Asserts that at a chance of zero the agent chooses the action the online
    network values highest, evaluating it with autograd recording nothing,
    under `torch.inference_mode`.
    """
    agent = build(epsilon_end=0, epsilon_start=0)
    modes = []

    with no_grad():
        values = agent.online(
            {key: as_tensor(stack)[None] for key, stack in observation.items()}
        )

    agent.online.register_forward_hook(
        lambda *_: modes.append(is_inference_mode_enabled())
    )

    assert agent.act(observation) == values.argmax().item()
    assert modes == [True]


def test_a_random_action_reaches_every_action_the_network_values(
    build       : Callable[..., DQN],
    observation : dict[str, ndarray]
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


def test_a_restore_refuses_a_checkpoint_reading_fewer_flags(
    build : Callable[..., DQN],
    space : Dict
):
    """
    Asserts that a checkpoint of a network reading four flags, as one
    written before `Event` declared the flags past the starter, is refused
    by an agent reading a flag for each member `Event` declares.
    """
    agent = DQN(
        actions  = 7,
        seed     = 1,
        settings = AgentSettings(device="cpu"),
        space    = Dict({**space.spaces, Entry.FLAGS: MultiBinary((1, len(Event)))}),
        steps    = 1000
    )

    with raises(ValueError, match="the checkpoint's networks differ from the agent's"):
        agent.restore(build().checkpoint)


def test_a_restore_refuses_networks_of_another_shape(build: Callable[..., DQN]):
    """
    Asserts that restoring a checkpoint whose online network holds entries
    another network declares raises `ValueError`, the error the commands
    refuse, in place of the `RuntimeError` `load_state_dict` raises.
    """
    checkpoint = build().checkpoint.model_copy(
        update = {"online": Linear(2, 1).state_dict()}
    )

    with raises(ValueError, match="the checkpoint's networks differ from the agent's"):
        build(seed=2).restore(checkpoint)


@mark.parametrize(
    ("seed", "same"),
    [param(1, True, id="the-same-seed"), param(2, False, id="another-seed")]
)
def test_a_seed_builds_the_online_networks_weights(
    build : Callable[..., DQN],
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


def test_a_restored_agent_draws_what_the_saved_agent_would(
    build  : Callable[..., DQN],
    play   : Callable[..., None],
    resume : Callable[[DQN], DQN]
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


def test_a_restored_agent_holds_the_saved_agents_replay_memory(
    build  : Callable[..., DQN],
    play   : Callable[..., None],
    resume : Callable[[DQN], DQN]
):
    """
    Asserts that an agent restoring a checkpoint holds every transition
    the saved agent's replay memory held, drawing the batch the saved agent
    draws.
    """
    saved = build()
    play(saved, 40)
    restored = resume(saved)

    assert restored.replay.held.sum() == saved.replay.held.sum() == 40
    assert_close(
        restored.replay.sample("cpu", 32).model_dump(),
        saved.replay.sample("cpu", 32).model_dump(),
        atol = 0,
        rtol = 0
    )


def test_a_restored_agent_keeps_training_from_the_saved_state(
    build  : Callable[..., DQN],
    play   : Callable[..., None],
    resume : Callable[[DQN], DQN]
):
    """
    Asserts that an agent restoring a checkpoint takes the saved agent's
    networks and step count, and that its next update moves its own
    online network, Adam counting that update after the saved ones, so the
    optimizer steps the parameters the checkpoint loaded into.
    """
    saved = build(warmup_steps=32)
    play(saved, 32)
    saved.update()
    saved.update()
    restored = resume(saved)

    assert restored.step == saved.step
    assert_close(
        (restored.online.state_dict(), restored.target.state_dict()),
        (saved.online.state_dict(), saved.target.state_dict()),
        atol = 0,
        rtol = 0
    )

    play(restored, 32)
    online = parameters_to_vector(restored.online.parameters())
    restored.update()

    assert not equal(parameters_to_vector(restored.online.parameters()), online)
    assert {state["step"].item() for state in restored.optimizer.state.values()} == {3}


@mark.parametrize(
    ("setting", "value", "read"),
    [
        param(
            "capacity",
            64,
            lambda agent: len(agent.replay.held),
            id = "the-slots-replay-memory-holds"
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
    build   : Callable[..., DQN],
    read    : Callable[[DQN], object],
    setting : str,
    value   : object
):
    """
    Asserts that the agent sizes replay memory and sets Adam's learning rate
    from the settings it is built with rather than from any default.
    """
    assert read(build(**{setting: value})) == value


@mark.parametrize(
    ("threads", "count"),
    [param(None, 2, id="no-count-named"), param(1, 1, id="one-thread-named")]
)
@mark.usefixtures("two_threads")
def test_building_an_agent_sets_the_thread_count_its_settings_name(
    build   : Callable[..., DQN],
    count   : int,
    threads : int | None
):
    """
    Asserts that building an agent sets the threads PyTorch runs on to the
    `threads` its settings name, and leaves the two `two_threads` set where
    they name none.
    """
    build(threads=threads)

    assert get_num_threads() == count


def test_a_step_both_intervals_divide_copies_the_target_before_its_update(
    build : Callable[..., DQN],
    play  : Callable[..., None]
):
    """
    Asserts that on a step `sync_steps` and `update_steps` both divide, the
    target network takes the online network's parameters before that step's
    update moves them, so the target holds the online network as it stood
    before the update.
    """
    agent = build(
        batch_size   = 4,
        sync_steps   = 4,
        update_steps = 4,
        warmup_steps = 4
    )
    play(agent, 4)
    synced = parameters_to_vector(agent.online.parameters())
    agent.update()

    assert equal(parameters_to_vector(agent.target.parameters()), synced)
    assert not equal(parameters_to_vector(agent.online.parameters()), synced)


@mark.parametrize(
    "reseed",
    [
        param("torch.cuda.manual_seed_all", id="cuda"),
        param("torch.mps.manual_seed",      id="mps")
    ]
)
def test_building_an_agent_reseeds_no_accelerators_generator(
    build       : Callable[..., DQN],
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


def test_an_update_changes_the_online_network_and_leaves_the_target_alone(
    build : Callable[..., DQN],
    play  : Callable[..., None]
):
    """
    Asserts that one update on a batch drawn from replay memory moves the
    online network's parameters and leaves every parameter of the target
    network as it was.
    """
    agent = build(warmup_steps=32)
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
    build : Callable[..., DQN],
    play  : Callable[..., None]
):
    """
    Asserts that the gradient Adam steps on carries a norm of
    `max_grad_norm`, read through a hook that runs before the step.
    """
    agent = build(max_grad_norm=1e-3, warmup_steps=32)
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
    build : Callable[..., DQN],
    play  : Callable[..., None]
):
    """
    Asserts that an update leaves each parameter holding the gradient of its
    own batch alone, whatever gradient the parameter held before it.
    """
    agent = build(warmup_steps=32)
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


def test_an_update_returns_the_loss_it_steps_on_and_the_batchs_mean_value(
    build       : Callable[..., DQN],
    monkeypatch : MonkeyPatch,
    play        : Callable[..., None]
):
    """
    Asserts that an update returns the Huber loss it takes its gradient
    step on and the mean of the values the online network gave the batch's
    actions, both read before the step moves the network.
    """
    agent = build(warmup_steps=32)
    read  = []
    play(agent, 32)

    def spy(values: Tensor, targets: Tensor) -> Tensor:  # prose: ignore[unsorted-positionals]
        """
        Computes the update's loss, recording it beside the mean value.
        """
        loss = huber_loss(values, targets)
        read.extend([loss.item(), values.mean().item()])

        return loss

    monkeypatch.setattr("squirtl.agent.learner.huber_loss", spy)
    update = agent.update()

    assert [update.loss, update.value] == read


def test_building_an_agent_leaves_torchs_global_generator_alone(
    build: Callable[..., DQN]
):
    """
    Asserts that building an agent leaves the state of PyTorch's global CPU
    generator as it found it, since the weights draw from a fork of it.
    """
    manual_seed(5)
    build()

    assert equal(get_rng_state(), manual_seed(5).get_state())


def test_building_an_agent_turns_nnpack_off(build: Callable[..., DQN]):
    """
    Asserts that building an agent inside a block holding NNPACK on turns
    it off for the whole process. `set_flags` returns the flag it replaces,
    which reads that state back, and the block restores the flag it found
    once it ends.
    """
    with nnpack.flags(enabled=True):
        build()

        assert nnpack.set_flags(True) == (False,)


def test_each_update_of_one_seed_moves_the_network_alike(
    batched : dict[str, ndarray],
    collect : Callable[[RolloutAgent], None],
    rolling : Callable[..., RolloutAgent]
):
    """
    Asserts that two PPO agents of one seed end an update holding the same
    weights, each epoch's minibatches drawn from their generators alone.
    """
    agents = [rolling(Algorithm.PPO), rolling(Algorithm.PPO)]

    for agent in agents:
        collect(agent)
        agent.update(batched)

    assert equal(
        parameters_to_vector(agents[0].network.parameters()),
        parameters_to_vector(agents[1].network.parameters())
    )


@each_agent
def test_each_agent_allocates_a_rollout_of_the_steps_its_own_settings_name(
    algorithm : Algorithm,
    rolling   : Callable[..., RolloutAgent]
):
    """
    Asserts that an agent's rollout holds the rows its own record names,
    whatever the other agent's default, and a column per environment.
    """
    assert rolling(algorithm, rollout_steps=3).rollout.rewards.shape == (3, 2)


@mark.parametrize(
    ("algorithm", "network", "normalized", "optimizer", "rate"),
    [
        param(Algorithm.PPO, ActorCritic, False, AdamW, 3e-4,   id="ppo"),
        param(Algorithm.PQN, QNetwork,    True,  RAdam, 2.5e-4, id="pqn")
    ]
)
def test_each_agent_trains_the_network_and_the_optimizer_its_source_sets(
    algorithm  : Algorithm,
    network    : type[Module],
    normalized : bool,
    optimizer  : type[Optimizer],
    rate       : float,
    rolling    : Callable[..., RolloutAgent]
):
    """
    Asserts that PPO trains its actor-critic with AdamW at Pleines et al.'s
    learning rate, and PQN its layer-normalized Q-network with RAdam at
    Gallici et al.'s, each optimizer built over the network's parameters.
    """
    agent = rolling(algorithm)

    assert type(agent.network) is network
    assert any(
        isinstance(layer, LayerNorm) for layer in agent.network.modules()
    ) is normalized
    assert type(agent.optimizer) is optimizer
    assert agent.optimizer.param_groups[0]["lr"] == rate
    assert agent.optimizer.param_groups[0]["params"] == list(agent.network.parameters())


@each_agent
def test_a_seed_builds_each_agents_network_and_leaves_pytorchs_generator_alone(
    algorithm : Algorithm,
    rolling   : Callable[..., RolloutAgent]
):
    """
    Asserts that two agents of one seed start from the same weights and
    a third of another seed does not, none of the three moving PyTorch's
    global generator.
    """
    manual_seed(5)
    first, second, third = (rolling(algorithm, seed=seed) for seed in (1, 1, 2))

    assert equal(get_rng_state(), manual_seed(5).get_state())
    assert equal(
        parameters_to_vector(first.network.parameters()),
        parameters_to_vector(second.network.parameters())
    )
    assert not equal(
        parameters_to_vector(first.network.parameters()),
        parameters_to_vector(third.network.parameters())
    )


def test_ppo_draws_its_samples_from_its_own_generator(
    batched : dict[str, ndarray],
    rolling : Callable[..., RolloutAgent]
):
    """
    Asserts that two PPO agents of one seed sample the same actions, leaving
    PyTorch's global generator as it was.
    """
    first, second = rolling(Algorithm.PPO), rolling(Algorithm.PPO)
    manual_seed(5)
    drawn = [
        [agent.act(batched).tolist() for _ in range(20)] for agent in (first, second)
    ]

    assert drawn[0] == drawn[1]
    assert equal(get_rng_state(), manual_seed(5).get_state())


def test_ppo_reads_each_advantage_and_clips_each_value_from_the_value_it_stored(
    rolling: Callable[..., RolloutAgent]
):
    """
    Asserts that on a critic reading 0, returns of 1 and 0 and old values of
    2 and -1 give advantages of -1 and 1, whose normalized gains on ratios
    of 2 and 1 give the objective's loss, and that the value's loss clips
    about each old value, the mean of the larger squared errors 1 and 0.64.
    """
    agent = rolling(Algorithm.PPO)
    flat([0.0] * 7, agent.network.policy)
    flat([0.0], agent.network.critic)
    uniform     = log(1 / 7)
    _, measures = agent.learn(
        batch_of(
            log_probs = [uniform - log(2), uniform],
            returns   = [1.0, 0.0],
            values    = [2.0, -1.0]
        )
    )

    assert measures[3:].tolist() == approx([0.5 / 2**0.5, 0.82], abs=1e-5)


@mark.parametrize(
    ("step", "epsilon"),
    [
        param(0,    1.0,    id="the-first-step"),
        param(50,   0.5005, id="halfway-through-exploration"),
        param(100,  0.001,  id="the-end-of-exploration"),
        param(1000, 0.001,  id="the-last-step")
    ]
)
def test_pqns_chance_of_a_random_action_falls_as_gallici_et_al_set_it(
    epsilon : float,
    rolling : Callable[..., RolloutAgent],
    step    : int
):
    """
    Asserts that PQN's chance falls linearly from 1 to 0.001 over the first
    tenth of a 1,000-step run, counted in environment steps, and holds at
    0.001 after it.
    """
    agent      = rolling(Algorithm.PQN)
    agent.step = step

    assert agent.epsilon == approx(epsilon)


def test_ppo_samples_each_action_from_its_policy(
    batched : dict[str, ndarray],
    rolling : Callable[..., RolloutAgent]
):
    """
    Asserts that PPO reads no chance of a random action, samples the one
    action a policy all but certain of it holds, and stores that action, a
    log-probability near 0, and the critic's value in the rollout's first
    row.
    """
    agent = rolling(Algorithm.PPO)
    flat(100 * one_hot(tensor(3), 7), agent.network.policy)
    flat([2.5], agent.network.critic)

    assert agent.epsilon is None
    assert agent.act(batched).tolist() == [3, 3]
    assert agent.rollout.actions[0].tolist() == [3, 3]
    assert agent.rollout.log_probs[0].tolist() == approx([0.0, 0.0])
    assert agent.rollout.values[0].tolist() == [2.5, 2.5]


def test_ppo_stores_the_log_probability_of_the_action_it_samples(
    batched : dict[str, ndarray],
    rolling : Callable[..., RolloutAgent]
):
    """
    Asserts that under a policy weighing the first action at e times each
    other, PPO stores for each action sampled its log-probability under the
    softmax, reading one action of each kind across 200 samples.
    """
    agent = rolling(Algorithm.PPO)
    flat(one_hot(tensor(0), 7), agent.network.policy)
    total = exp(1) + 6
    seen  = set()

    for _ in range(100):
        actions = agent.act(batched).tolist()
        seen   |= set(actions)

        assert agent.rollout.log_probs[0].tolist() == approx(
            [(1 if action == 0 else 0) - log(total) for action in actions]
        )

    assert seen == set(range(7))


def test_pqn_draws_its_random_actions_from_its_own_generator(
    batched : dict[str, ndarray],
    rolling : Callable[..., RolloutAgent]
):
    """
    Asserts that at a chance of one PQN reaches every action, that two
    agents of one seed draw the same actions, and that the draws leave
    PyTorch's global generator as it was.
    """
    first, second = rolling(Algorithm.PQN), rolling(Algorithm.PQN)
    manual_seed(5)
    drawn = [
        [agent.act(batched).tolist() for _ in range(100)] for agent in (first, second)
    ]

    assert drawn[0] == drawn[1]
    assert {action for pair in drawn[0] for action in pair} == set(range(7))
    assert equal(get_rng_state(), manual_seed(5).get_state())


@each_agent
def test_each_step_counts_one_environment_step_per_environment(
    algorithm : Algorithm,
    collect   : Callable[[RolloutAgent], None],
    rolling   : Callable[..., RolloutAgent]
):
    """
    Asserts that a rollout of four steps across two environments counts as
    eight environment steps and leaves the agent past the rollout's last
    row.
    """
    agent = rolling(algorithm)
    collect(agent)

    assert (agent.step, agent.rollout.row) == (8, 4)


@mark.parametrize(
    ("algorithm", "head", "bias", "value"),
    [
        param(Algorithm.PPO, "critic", [2.5],     2.5, id="the-critics-value"),
        param(Algorithm.PQN, "head",   arange(7), 6.0, id="the-highest-q-value")
    ]
)
def test_each_agent_values_a_batch_of_observations(
    algorithm : Algorithm,
    batched   : dict[str, ndarray],
    bias      : object,
    head      : str,
    rolling   : Callable[..., RolloutAgent],
    value     : float
):
    """
    Asserts that PPO values each observation at its critic's output and PQN
    at the highest value of its head, each a `float32` array of one value
    per observation.
    """
    agent = rolling(algorithm)
    flat(bias, getattr(agent.network, head))
    values = agent.value(batched)

    assert (values.tolist(), values.dtype) == ([value, value], float32)


@mark.parametrize(
    ("algorithm", "decay"),
    [param(Algorithm.PPO, 0.95, id="ppo"), param(Algorithm.PQN, 0.65, id="pqn")]
)
def test_an_update_reads_its_agents_decay_and_discount_and_the_last_value(
    algorithm   : Algorithm,
    batched     : dict[str, ndarray],
    collect     : Callable[[RolloutAgent], None],
    decay       : float,
    monkeypatch : MonkeyPatch,
    rolling     : Callable[..., RolloutAgent]
):
    """
    Asserts that an update computes its λ-returns at its agent's λ and the
    discount of 0.997, from the value of the observation each environment
    reached.
    """
    agent = rolling(algorithm)
    calls = []
    read  = Rollout.returns

    collect(agent)
    monkeypatch.setattr(
        Rollout,
        "returns",
        lambda rollout, *given: calls.append((*given, agent.value(batched)))
        or read(rollout, *given)
    )
    agent.update(batched)

    assert [(given[0], given[1], given[2].tolist()) for given in calls] == [
        (decay, 0.997, calls[0][3].tolist())
    ]


@mark.parametrize(
    ("algorithm", "epochs", "minibatches"),
    [param(Algorithm.PPO, 3, 2, id="ppo"), param(Algorithm.PQN, 2, 4, id="pqn")]
)
def test_an_update_takes_a_step_per_minibatch_covering_the_rollout_each_epoch(
    algorithm   : Algorithm,
    batched     : dict[str, ndarray],
    collect     : Callable[[RolloutAgent], None],
    epochs      : int,
    minibatches : int,
    monkeypatch : MonkeyPatch,
    rolling     : Callable[..., RolloutAgent]
):
    """
    Asserts that an update over a rollout of eight samples takes an
    optimizer step per minibatch of the epochs its source sets, three for
    PPO and two for PQN, each epoch reading every sample once in an order of
    its own, and that the rollout's next step lands on its first row.
    """
    agent = rolling(algorithm, minibatches)
    learn = agent.learn
    read  = []
    step  = agent.optimizer.step
    steps = []

    collect(agent)
    agent.rollout.values[:] = arange(8.0).reshape(4, 2).numpy()
    monkeypatch.setattr(
        agent,
        "learn",
        lambda batch: read.append(batch["values"].tolist()) or learn(batch)
    )
    monkeypatch.setattr(agent.optimizer, "step", lambda: steps.append(1) or step())
    agent.update(batched)

    orders = [
        sum(read[epoch * minibatches :][: minibatches], [])
        for epoch in range(epochs)
    ]

    assert [sorted(order) for order in orders] == [list(range(8))] * epochs
    assert len({tuple(order) for order in orders}) == epochs
    assert (
        len(read),
        len(steps),
        agent.rollout.row
    ) == (epochs * minibatches, epochs * minibatches, 0)


@each_agent
def test_an_update_moves_the_network(
    algorithm : Algorithm,
    batched   : dict[str, ndarray],
    collect   : Callable[[RolloutAgent], None],
    rolling   : Callable[..., RolloutAgent]
):
    """
    Asserts that one update moves the parameters of the agent's network.
    """
    agent = rolling(algorithm)
    collect(agent)
    before = parameters_to_vector(agent.network.parameters()).clone()
    agent.update(batched)

    assert not equal(parameters_to_vector(agent.network.parameters()), before)


@mark.parametrize(
    ("algorithm", "norm"),
    [param(Algorithm.PPO, 0.5, id="ppo"), param(Algorithm.PQN, 10.0, id="pqn")]
)
def test_an_update_clips_each_gradient_at_its_agents_maximum_norm(
    algorithm   : Algorithm,
    batched     : dict[str, ndarray],
    collect     : Callable[[RolloutAgent], None],
    monkeypatch : MonkeyPatch,
    norm        : float,
    rolling     : Callable[..., RolloutAgent]
):
    """
    Asserts that each gradient step clips the gradient at the maximum norm
    Pleines et al. set for PPO and Gallici et al.'s Atari settings set for
    PQN.
    """
    agent = rolling(algorithm)
    norms = []
    collect(agent)
    monkeypatch.setattr(
        "squirtl.agent.learner.clip_grad_norm_",
        lambda parameters, limit: norms.append(limit) or clip_grad_norm_(
            parameters,
            limit
        )
    )
    agent.update(batched)

    assert set(norms) == {norm}


@mark.parametrize(
    ("algorithm", "record", "count"),
    [
        param(Algorithm.PPO, PolicyUpdate, 6, id="ppo"),
        param(Algorithm.PQN, Update,       4, id="pqn")
    ]
)
def test_an_update_averages_each_measure_over_its_minibatches(
    algorithm   : Algorithm,
    batched     : dict[str, ndarray],
    collect     : Callable[[RolloutAgent], None],
    count       : int,
    monkeypatch : MonkeyPatch,
    record      : type[Measures],
    rolling     : Callable[..., RolloutAgent]
):
    """
    Asserts that an update returns its agent's record of measures, each the
    mean over the two minibatches of each epoch of what `learn` read, which
    the stand-in numbers from 1 up on each measure.
    """
    agent = rolling(algorithm)
    learn = agent.learn
    taken = []

    def numbered(batch: dict[str, Tensor]) -> tuple[Tensor, Tensor]:
        """
        Takes the real loss on `batch` beside measures of the minibatch's
        number.
        """
        taken.append(True)

        return learn(batch)[0], full((len(record.model_fields),), float(len(taken)))

    collect(agent)
    monkeypatch.setattr(agent, "learn", numbered)
    update = agent.update(batched)

    assert type(update) is record
    assert update.totals == approx(((count + 1) / 2,) * len(record.model_fields))


def test_pqn_takes_the_action_its_network_values_highest_at_a_chance_of_zero(
    batched : dict[str, ndarray],
    rolling : Callable[..., RolloutAgent]
):
    """
    Asserts that at a chance of zero PQN takes the action its head values
    highest in each environment and stores the action and its value in the
    rollout's first row.
    """
    agent = rolling(Algorithm.PQN, epsilon_end=0.0, epsilon_start=0.0)
    flat(3 * one_hot(tensor(2), 7), agent.network.head)

    assert agent.act(batched).tolist() == [2, 2]
    assert agent.rollout.actions[0].tolist() == [2, 2]
    assert agent.rollout.values[0].tolist() == [3.0, 3.0]


@mark.parametrize(
    ("old", "fields", "losses"),
    [
        param(
            log(1 / 7) - log(2),
            {"returns": [1.0, -1.0], "values": [0.0, 0.0]},
            {
                "clipped"     : 1.0,
                "entropy"     : log(7),
                "kl"          : 1 - log(2),
                "policy_loss" : (2 - 1.2) / 2**0.5 / 2,
                "value_loss"  : 1.0
            },
            id = "a-ratio-of-two-clipped-on-the-gaining-sample-alone"
        ),
        param(
            log(1 / 7),
            {"returns": [1.0, 1.0], "values": [0.0, 0.0]},
            {
                "clipped"     : 0.0,
                "entropy"     : log(7),
                "kl"          : 0.0,
                "policy_loss" : 0.0,
                "value_loss"  : 1.0
            },
            id = "no-ratio-to-clip-and-no-advantage"
        )
    ]
)
def test_ppo_trains_on_the_clipped_objective_beside_the_values_loss(
    fields  : dict[str, list[float]],
    losses  : dict[str, float],
    old     : float,
    rolling : Callable[..., RolloutAgent]
):
    """
    Asserts that under a uniform policy and a critic reading 0, the
    objective takes the smaller of the ratio's and the clipped ratio's gain
    on the advantages each minibatch normalizes, and the loss adds half the
    value's squared error, with each measure worked by hand.
    """
    agent = rolling(Algorithm.PPO)
    flat([0.0] * 7, agent.network.policy)
    flat([0.0], agent.network.critic)
    loss, measures = agent.learn(batch_of(log_probs=[old, old], **fields))

    assert PolicyUpdate(**dict(zip(losses, measures.tolist()))).totals == approx(
        tuple(losses.values()),
        abs = 1e-5
    )
    assert loss.item() == approx(
        losses["policy_loss"] + 0.5 * losses["value_loss"],
        abs = 1e-5
    )


@mark.parametrize(
    ("critic", "value_loss"),
    [
        param(1.0, 0.64,  id="a-clipped-value-further-from-the-return"),
        param(0.1, 0.81,  id="a-value-inside-the-clip-range"),
        param(2.0, 1.0,   id="an-overshoot-further-than-its-clipped-value")
    ]
)
def test_ppos_value_loss_takes_the_larger_of_its_two_squared_errors(
    critic     : float,
    rolling    : Callable[..., RolloutAgent],
    value_loss : float
):
    """
    Asserts that on a return of 1 and an old value of 0, the value's loss
    is the larger of the new value's squared error and that of the value
    clipped to within 0.2 of the old one, as Pleines et al. clip it.
    """
    agent = rolling(Algorithm.PPO)
    flat([0.0] * 7, agent.network.policy)
    flat([critic], agent.network.critic)
    uniform     = log(1 / 7)
    _, measures = agent.learn(
        batch_of(
            log_probs = [uniform, uniform],
            returns   = [1.0, 1.0],
            values    = [0.0, 0.0]
        )
    )

    assert measures[4].item() == approx(value_loss)


def test_pqn_trains_on_half_the_squared_error_of_each_sampled_action(
    rolling: Callable[..., RolloutAgent]
):
    """
    Asserts that with every action valued at its index, the loss on the
    actions 1 and 3 toward returns of 2 and 1 is half the mean of the
    squared errors 1 and 4, beside a mean value of 2, each read from the
    action sampled rather than the one valued highest.
    """
    agent = rolling(Algorithm.PQN)
    flat(arange(7), agent.network.head)
    loss, measures = agent.learn(batch_of(actions=[1, 3], returns=[2.0, 1.0]))

    assert loss.item() == approx(1.25)
    assert measures.tolist() == approx([1.25, 2.0])


@each_agent
def test_a_restored_agent_trains_as_the_saved_agent_would(
    algorithm : Algorithm,
    batched   : dict[str, ndarray],
    collect   : Callable[[RolloutAgent], None],
    rolling   : Callable[..., RolloutAgent],
    tmp_path  : Path
):
    """
    Asserts that an agent of another seed restoring a saved checkpoint holds
    its step count, and that the next rollout and update of both agents end
    on the same weights and the same optimizer state, each drawing what the
    other draws.
    """
    saved = rolling(algorithm)
    collect(saved)
    saved.update(batched)
    saved.checkpoint.save(tmp_path / "checkpoint.npz")

    restored = rolling(algorithm, seed=2)
    restored.restore(RolloutCheckpoint.from_path(tmp_path / "checkpoint.npz"))

    assert restored.step == saved.step == 8

    for agent in (saved, restored):
        collect(agent)
        agent.update(batched)

    assert_close(
        restored.network.state_dict(),
        saved.network.state_dict(),
        atol = 0,
        rtol = 0
    )
    assert_close(
        restored.optimizer.state_dict(),
        saved.optimizer.state_dict(),
        atol = 0,
        rtol = 0
    )
    assert restored.generator.random() == saved.generator.random()


@each_agent
def test_a_restore_refuses_another_agents_network(
    algorithm : Algorithm,
    rolling   : Callable[..., RolloutAgent]
):
    """
    Asserts that restoring a checkpoint holding the network of the other
    agent raises `ValueError`, which `squirtl train` exits 1 on, in place of
    the `RuntimeError` `load_state_dict` raises.
    """
    other = Algorithm.PQN if algorithm is Algorithm.PPO else Algorithm.PPO

    with raises(ValueError, match="the checkpoint's networks differ from the agent's"):
        rolling(algorithm).restore(rolling(other).checkpoint)
