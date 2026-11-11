"""
Pins how `Evaluator` plays an evaluation's episodes, covering:

- Each episode's play depending on its number alone, however many
  environments the evaluation runs and whichever one it lands in
- The episodes of the random baseline and of the agent played across worker
  processes on PyBoy, and a worker ignoring the interrupt signal
- The policy taking the network's action or a random one from each
  environment's seeded action space, at the epsilon the settings name for
  the deep Q-network and PQN and at none for PPO, which plays its most likely
  action, leaving PyTorch's global generator as it found it
"""

from collections.abc   import Callable
from common.evaluation import outcome
from gymnasium         import Env
from gymnasium.spaces  import Box, Dict, Discrete
from gymnasium.vector  import AutoresetMode, SyncVectorEnv
from numpy             import ndarray, uint8, zeros
from os                import kill
from pytest            import MonkeyPatch, fixture, mark, param, raises
from signal            import SIGINT
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
    "network",
    [
        param(None,           id="the-baseline"),
        param(value_the_last, id="the-agent")
    ]
)
def test_each_episode_plays_alike_however_many_environments_run(
    evaluator : Callable[..., Evaluator],
    network   : Callable[[dict[str, Tensor]], Tensor] | None
):
    """
    Asserts that five episodes of differing lengths reach the same outcomes
    across one, two, or three environments, each episode's reset and random
    actions seeded by its number alone, under the random baseline and
    under an agent whose network values the last action highest, and that
    the episodes' lengths, which each reset's seed draws, differ from one
    another.
    """
    played = [
        evaluator(environments=environments, episodes=5).play(
            Policy(epsilon=0.5, network=network)
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


@mark.parametrize(
    ("algorithm", "epsilon"),
    [
        param(Algorithm.DQN, 0.05, id="the-deep-q-network"),
        param(Algorithm.PPO, 0.0,  id="ppos-most-likely-action"),
        param(Algorithm.PQN, 0.05, id="pqn")
    ]
)
def test_each_agent_plays_its_network_at_its_epsilon(
    algorithm   : Algorithm,
    epsilon     : float,
    evaluator   : Callable[..., Evaluator],
    monkeypatch : MonkeyPatch
):
    """
    Asserts that an evaluation builds the agent's own network from its
    weights and plays it at the epsilon the evaluation settings name, 0.05
    by default, for the deep Q-network and PQN, and at 0 for PPO, whereas
    the baseline plays every action at random.
    """
    policies = []
    monkeypatch.setattr(
        Evaluator,
        "play",
        lambda evaluator, policy: policies.append(policy) or [outcome()]
    )

    with evaluator(algorithm, environments=1, episodes=1) as started:
        built = acting_network(
            started.envs.single_action_space.n,
            algorithm,
            started.envs.single_observation_space
        )
        started.evaluate(Weights(online=built.state_dict(), step=9))
        started.baseline()

    assert [(policy.epsilon, policy.network is None) for policy in policies] == [
        (epsilon, False),
        (1.0, True)
    ]
    assert type(policies[0].network) is type(built)
    assert_close(policies[0].network.state_dict(), built.state_dict(), atol=0, rtol=0)


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
    generator as it found it.
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
