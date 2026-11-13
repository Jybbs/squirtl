"""
Pins how `Evaluator` plays an evaluation's episodes, covering:

- Each episode's play depending on its number alone, however many
  environments the evaluation runs and whichever one it lands in
- The episodes of the random baseline and of the agent played across worker
  processes on PyBoy, a worker ignoring the interrupt signal, and an
  interrupt partway through a step terminating each worker
- The policy taking the network's action or a random one from each
  environment's seeded action space, at the epsilon the settings name for
  the deep Q-network and PQN, and for PPO drawing each action from its
  policy through that space's generator and again taking its most likely
  action, leaving PyTorch's global generator as it found it
"""

from collections.abc   import Callable
from common.evaluation import outcome
from gymnasium         import Env
from gymnasium.spaces  import Box, Dict, Discrete
from gymnasium.vector  import AutoresetMode, SyncVectorEnv
from numpy             import ndarray, uint8, zeros
from os                import kill
from pytest            import MonkeyPatch, fail, fixture, mark, param, raises
from signal            import ITIMER_REAL, SIGALRM, SIGINT, SIGTERM, setitimer, signal
from torch             import Tensor, arange, equal, get_rng_state, no_grad, tensor
from torch.testing     import assert_close
from typing            import Any

from squirtl.agent.checkpoint      import Weights
from squirtl.agent.networks        import ActorCritic, acting_network
from squirtl.agent.schemas         import Algorithm
from squirtl.emulator.schemas      import Cartridge, EmulatorSettings
from squirtl.environment.overworld import Overworld
from squirtl.environment.schemas   import EnvironmentSettings, Outcome
from squirtl.evaluation.evaluator  import Evaluator, Policy
from squirtl.evaluation.schemas    import EvaluationSettings
from squirtl.reward.schemas        import Event, RewardSettings, Term


class Tally(Env):
    """
    Stands in for the environment, each episode lasting the one to four
    steps its reset's seed draws and returning the sum of its actions, which
    its last step reports as its outcome.
    """

    action_space      = Discrete(7)
    observation_space = Dict({"frames": Box(0, 255, (1,), uint8)})

    def reset(
        self,
        *,
        options : dict[str, Any] | None = None,
        seed    : int | None            = None
    ) -> tuple[dict[str, ndarray], dict[str, Any]]:
        """
        Draws the episode's length from the generator `seed` seeds.
        """
        super().reset(seed=seed)
        self.actions = []
        self.length  = int(self.np_random.integers(1, 5))

        return {"frames": zeros(1, uint8)}, {}

    def step(self, action: int) -> tuple[dict[str, ndarray], float, bool, bool, dict]:
        """
        Records `action` and reports the episode's outcome once it has taken
        its length's steps.
        """
        self.actions.append(int(action))
        ended = len(self.actions) >= self.length

        return {"frames": zeros(1, uint8)}, 0.0, ended, False, {
            "outcome": Outcome(
                length     = len(self.actions),
                positions  = 1,
                reward     = float(sum(self.actions)),
                seconds    = 0.0,
                shares     = dict.fromkeys(Term, 0.0),
                terminated = True
            )
        } if ended else {}


def value_the_last(observations: dict[str, Tensor]) -> Tensor:
    """
    Stands in for the network, valuing the last of the seven actions highest
    for each observation in the batch.
    """
    return tensor([[0.0] * 6 + [1.0]] * len(observations["frames"]))


@fixture
def evaluator(cartridge: Cartridge) -> Callable[..., Evaluator]:
    """
    Builds a factory of evaluators on `cartridge` on the CPU from seed 1,
    under episodes of three steps ending at the starter unless the call
    names another goal, and the evaluation settings any keyword sets,
    playing the deep Q-network unless the call names another agent.
    """

    def build(
        algorithm  : Algorithm = Algorithm.DQN,
        goal       : Event     = Event.EVENT_GOT_STARTER,
        **settings : object
    ) -> Evaluator:
        """
        Starts the evaluator of `algorithm` toward `goal` that `settings`
        describe.
        """
        return Evaluator(
            algorithm,
            "cpu",
            1,
            EvaluationSettings(**settings),
            Overworld.specification(
                cartridge,
                EmulatorSettings(),
                EnvironmentSettings(goal=goal, max_episode_steps=3),
                RewardSettings()
            )
        )

    return build


@fixture
def tallied(monkeypatch: MonkeyPatch):
    """
    Makes each evaluator run its environments as `Tally` in this process,
    which `SyncVectorEnv` steps one after the other under the same reset
    `play` asks of the worker processes.
    """
    monkeypatch.setattr(
        "squirtl.evaluation.evaluator.make_vec",
        lambda specification, num_envs, **_: SyncVectorEnv(
            [Tally] * num_envs,
            autoreset_mode = AutoresetMode.DISABLED
        )
    )


@mark.usefixtures("tallied")
@mark.parametrize(
    ("network", "sampled"),
    [
        param(None,           False, id="the-baseline"),
        param(value_the_last, False, id="the-agent"),
        param(value_the_last, True,  id="ppos-sampled-policy")
    ]
)
def test_each_episode_plays_alike_however_many_environments_run(
    evaluator : Callable[..., Evaluator],
    network   : Callable[[dict[str, Tensor]], Tensor] | None,
    sampled   : bool
):
    """
    Asserts that five episodes of differing lengths reach the same outcomes
    across one, two, or three environments, each episode's reset and random
    actions seeded by its number alone, under the random baseline and
    under an agent whose network values the last action highest, played
    epsilon-greedily and sampled from its logits as PPO's is, and that
    the episodes' lengths, which each reset's seed draws, differ from one
    another.
    """
    played = [
        evaluator(environments=environments, episodes=5).play(
            Policy(epsilon=0.5, network=network, sampled=sampled)
        )
        for environments in (1, 2, 3)
    ]

    assert played[0] == played[1] == played[2]
    assert len({outcome.length for outcome in played[0]}) > 1


def test_a_policy_takes_the_largest_logit_of_ppos_network_at_no_chance():
    """
    Asserts that PPO's network, whose forward pass reads the policy's
    logits, plays the most likely action of each observation at an epsilon
    of 0.
    """
    network = ActorCritic(7, Dict(frames=Box(0, 255, (4, 36, 36), uint8)))

    with no_grad():
        network.policy.weight.zero_()
        network.policy.bias.copy_(arange(7.0))

    acted = Policy(epsilon=0.0, network=network).act(
        {"frames": zeros((2, 4, 36, 36), uint8)},
        [Discrete(7, seed=seed) for seed in (0, 1)]
    )

    assert acted.tolist() == [6, 6]


def test_a_sampled_policy_draws_each_action_from_its_spaces_generator():
    """
    Asserts that a sampled policy over logits even across the seven
    actions draws the actions the Gumbel-max trick takes from each space's
    generator, the same again from spaces seeded alike and spread over
    several actions, whereas logits far apart take the largest every time.
    """
    frames = {"frames": zeros((64, 1), uint8)}
    flat   = Policy(network=lambda observations: tensor([[0.0] * 7] * 64), sampled=True)
    spaces = lambda: [Discrete(7, seed=seed) for seed in range(64)]
    drawn  = flat.act(frames, spaces()).tolist()
    gumbel = [space.np_random.gumbel(size=7).argmax() for space in spaces()]
    peaked = Policy(
        network = lambda observations: tensor([[0.0] * 6 + [50.0]] * 64),
        sampled = True
    )

    assert drawn == gumbel == flat.act(frames, spaces()).tolist()
    assert len(set(drawn)) > 1
    assert set(peaked.act(frames, spaces()).tolist()) == {6}


@mark.parametrize(
    ("algorithm", "played"),
    [
        param(Algorithm.DQN, [(0.05, False)],              id="the-deep-q-network"),
        param(
            Algorithm.PPO,
            [(0.0, False), (0.0, True)],
            id = "ppo-sampled-and-at-its-mode"
        ),
        param(Algorithm.PQN, [(0.05, False)],              id="pqn")
    ]
)
def test_each_agent_plays_its_network_as_it_trains(
    algorithm   : Algorithm,
    evaluator   : Callable[..., Evaluator],
    monkeypatch : MonkeyPatch,
    played      : list[tuple[float, bool]]
):
    """
    Asserts that an evaluation builds the agent's own network from its
    weights and plays it at the epsilon the evaluation settings name, 0.05
    by default, for the deep Q-network and PQN, and for PPO plays it at its
    most likely action and then sampled from its policy, recording the first
    beside the second, whereas the baseline plays every action at random.
    """
    policies = []
    monkeypatch.setattr(
        Evaluator,
        "play",
        lambda evaluator, policy: policies.append(policy) or [outcome(len(policies))]
    )

    with evaluator(algorithm, environments=1, episodes=1) as started:
        built = acting_network(
            started.envs.single_action_space.n,
            algorithm,
            started.envs.single_observation_space
        )
        evaluation = started.evaluate(Weights(online=built.state_dict(), step=9))
        baseline   = started.baseline()

    assert [
        (policy.epsilon, policy.sampled, policy.network is None) for policy in policies
    ] == [(*each, False) for each in played] + [(1.0, False, True)]
    assert type(policies[0].network) is type(built)
    assert_close(policies[0].network.state_dict(), built.state_dict(), atol=0, rtol=0)
    assert (
        evaluation.outcomes[0].reward,
        None if evaluation.argmax is None else evaluation.argmax[0].reward,
        baseline.argmax
    ) == ((2.0, 1.0) if algorithm.sampled else (1.0, None)) + (None,)


def test_a_worker_plays_on_through_an_interrupt(evaluator: Callable[..., Evaluator]):
    """
    Asserts that the interrupt signal reaching each worker process, as a
    terminal sends it every process in its foreground group, leaves the
    evaluation playing its episodes rather than ending it.
    """
    with evaluator(environments=2, episodes=2) as started:
        for process in started.envs.processes:
            kill(process.pid, SIGINT)

        assert len(started.baseline().outcomes) == 2


def test_an_evaluation_refuses_weights_another_agents_network_holds(
    evaluator: Callable[..., Evaluator]
):
    """
    Asserts that evaluating the deep Q-network on the weights of PPO's
    network, whose entries differ from its own, raises a `ValueError` naming
    the difference rather than PyTorch's `RuntimeError`.
    """
    with evaluator(environments=1, episodes=1) as started:
        online = acting_network(
            started.envs.single_action_space.n,
            Algorithm.PPO,
            started.envs.single_observation_space
        ).state_dict()

        with raises(
            ValueError,
            match = "the checkpoint's networks differ from the agent's"
        ):
            started.evaluate(Weights(online=online, step=9))


@mark.filterwarnings("ignore:.*pending call to .step")
def test_an_interrupt_partway_through_a_step_ends_each_worker(
    evaluator: Callable[..., Evaluator]
):
    """
    Asserts that an interrupt raised once a step has read some of the
    workers' pipes ends the evaluation and terminates each worker, the alarm
    failing the case where closing the environments blocks on a pipe already
    read.
    """
    handler = signal(SIGALRM, lambda *_: fail("Closing blocked on a pipe already read"))

    with raises(KeyboardInterrupt), evaluator(environments=2, episodes=2) as started:
        vector = started.envs

        vector.reset(seed=1)
        vector.step_async(zeros(vector.num_envs, int))
        vector.parent_pipes[0].recv()
        setitimer(ITIMER_REAL, 60)
        raise KeyboardInterrupt

    setitimer(ITIMER_REAL, 0)
    signal(SIGALRM, handler)

    assert {process.exitcode for process in vector.processes} == {-SIGTERM}


@mark.parametrize(
    ("epsilon", "chosen"),
    [
        param(0.0, [6, 6], id="the-network"),
        param(
            1.0,
            [Discrete(7, seed=seed).sample() for seed in (0, 1)],
            id = "the-action-space"
        )
    ]
)
def test_the_policy_takes_the_networks_action_or_one_its_space_samples(
    chosen  : list[int],
    epsilon : float
):
    """
    Asserts that the policy takes the action the network values highest at
    an epsilon of 0, and at an epsilon of 1 the action each environment's
    seeded space samples first.
    """
    acted = Policy(epsilon=epsilon, network=value_the_last).act(
        {"frames": zeros((2, 1), uint8)},
        [Discrete(7, seed=seed) for seed in (0, 1)]
    )

    assert acted.tolist() == chosen


@mark.usefixtures("tallied")
def test_an_evaluation_runs_no_more_environments_than_its_episodes(
    evaluator: Callable[..., Evaluator]
):
    """
    Asserts that an evaluation of two episodes runs two environments where
    its settings name eight, since a third would play no episode it keeps.
    """
    assert evaluator(environments=8, episodes=2).envs.num_envs == 2


@mark.parametrize(
    "algorithm",
    [
        param(Algorithm.DQN, id="the-deep-q-network"),
        param(Algorithm.PPO, id="ppo"),
        param(Algorithm.PQN, id="pqn")
    ]
)
def test_the_baseline_and_the_agent_play_their_episodes_across_worker_processes(
    algorithm : Algorithm,
    evaluator : Callable[..., Evaluator]
):
    """
    Asserts that two worker processes on PyBoy play the random baseline's
    three episodes and those of each agent, each truncated after three
    steps on the blank cartridge and each evaluation naming the run's goal,
    the agent's recording the step it read and leaving PyTorch's global
    generator as it found it, and each worker exiting cleanly once the
    evaluation closes.
    """
    with evaluator(algorithm, environments=2, episodes=3) as started:
        online = acting_network(
            started.envs.single_action_space.n,
            algorithm,
            started.envs.single_observation_space
        ).state_dict()
        state  = get_rng_state()
        played = [started.baseline(), started.evaluate(Weights(online=online, step=9))]

    assert equal(get_rng_state(), state)
    assert {process.exitcode for process in started.envs.processes} == {0}
    assert [
        (
            evaluation.goal, evaluation.step,
            [(o.length, o.terminated) for o in evaluation.outcomes]
        )
        for evaluation in played
    ] == [
        (Event.EVENT_GOT_STARTER, None, [(3, False)] * 3),
        (Event.EVENT_GOT_STARTER, 9, [(3, False)] * 3)
    ]


@mark.usefixtures("tallied")
def test_an_evaluation_names_the_goal_its_environment_settings_name(
    evaluator: Callable[..., Evaluator]
):
    """
    Asserts that the random baseline's evaluation names the goal the
    environment's settings name, here the Pokédex rather than the default.
    """
    evaluation = evaluator(episodes=1, goal=Event.EVENT_GOT_POKEDEX).baseline()

    assert evaluation.goal is Event.EVENT_GOT_POKEDEX
