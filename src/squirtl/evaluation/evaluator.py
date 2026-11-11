"""
Defines `Evaluator`, which plays an evaluation's episodes across the
environments `gymnasium.make_vec` runs in parallel, and `Policy`, the
epsilon-greedy policy it plays.
"""

from collections.abc import Callable, Mapping, Sequence
from contextlib      import AbstractContextManager
from copy            import deepcopy
from gymnasium       import make_vec
from gymnasium.envs.registration import EnvSpec
from gymnasium.spaces            import Discrete
from gymnasium.vector            import AutoresetMode
from itertools    import count
from numpy        import array, flatnonzero, ndarray, ones, uint64, where
from numpy.random import SeedSequence
from torch        import Tensor, inference_mode
from torch.random import fork_rng

from squirtl.agent.checkpoint    import Weights
from squirtl.agent.learner       import matching_networks
from squirtl.agent.networks      import acting_network, tensors
from squirtl.agent.schemas       import Algorithm
from squirtl.emulator.schemas    import Record, UnitInterval
from squirtl.environment.schemas import Outcome
from squirtl.environment.workers import ignore_interrupts
from squirtl.evaluation.schemas  import Evaluation, EvaluationSettings


class Policy(Record):
    """
    The policy an evaluation plays, choosing a random action with
    probability `epsilon` and otherwise the action `network` scores highest,
    the highest value of a Q-network or the largest logit of PPO's policy,
    or a random action at every step where it holds no network. Each
    environment's random actions come from that environment's own action
    space, which the evaluation seeds for each episode.
    """

    device: str = "cpu"
    """
    The device `network` evaluates each batch on.
    """

    epsilon: UnitInterval = 1.0
    """
    The chance of a random action at each step.
    """

    network: Callable[[dict[str, Tensor]], Tensor] | None = None
    """
    The network scoring each action of a batch of observations, or `None`
    for the random baseline.
    """

    @inference_mode()
    def act(self, observations: Mapping[str, ndarray], spaces: Sequence[Discrete]) -> ndarray:
        """
        Chooses each environment's action from the batch of `observations`,
        sampling one from its space in `spaces` and then, where a network is
        held, drawing from that space's generator whether to keep it or take
        the action the network scores highest, which it evaluates without
        building an autograd graph.

        Returns:
            One action per environment, a `(len(spaces),)` array of `int64`.
        """
        actions = array([space.sample() for space in spaces])

        if self.network is None:
            return actions

        explore = array([space.np_random.random() < self.epsilon for space in spaces])
        greedy  = self.network(tensors(self.device, observations))

        return where(explore, actions, greedy.argmax(1).numpy(force=True))


class Evaluator(AbstractContextManager):
    """
    The environments an evaluation plays its episodes across, which
    `gymnasium.make_vec` runs in a worker process apiece, as many as the
    settings name and no more than their episodes. Episode `n` resets from
    the seed the evaluation stream's `SeedSequence` draws for its child `n`,
    and draws its random actions from an action space seeded alike, so its
    play depends on that number alone, whichever environment it lands in.
    """

    def __exit__(self, *raised: object):
        """
        Closes the environments and the processes running them, whether or
        not the `with` block raised.
        """
        self.envs.close()

    def __init__(
        self,
        algorithm     : Algorithm,
        device        : str,
        seed          : int,
        settings      : EvaluationSettings,
        specification : EnvSpec
    ):
        """
        Starts the environments `specification` describes, which reset
        an episode only when `play` asks, so the evaluation chooses each
        episode's seed, and reads the goal its environment settings name.

        Args:
            algorithm : The agent whose network each evaluation builds.
            device    : The device the agent's network evaluates each batch
                        on.
            seed      : The unsigned 64-bit seed of the run's evaluation
                        stream.
        """
        self.algorithm = algorithm
        self.device    = device
        self.envs      = make_vec(
            specification,
            num_envs      = min(settings.environments, settings.episodes),
            vector_kwargs = {
                "autoreset_mode" : AutoresetMode.DISABLED,
                "worker"         : ignore_interrupts
            },
            vectorization_mode = "async"
        )
        self.goal     = specification.kwargs["environment"].goal
        self.seed     = seed
        self.settings = settings

    def baseline(self) -> Evaluation:
        """
        Plays the random baseline's episodes, every action sampled from the
        seeded action space.
        """
        return Evaluation(
            goal     = self.goal,
            outcomes = self.play(Policy()),
            step     = None
        )

    def evaluate(self, weights: Weights) -> Evaluation:
        """
        Plays the episodes of the agent's network holding `weights`, at
        their step, epsilon-greedily for the deep Q-network and PQN and
        taking PPO's most likely action at every step, as Mhammedi and Cohan
        evaluate the agents their PPO trains. The network is built anew,
        under a fork of PyTorch's global generator, so the evaluation leaves
        the agent and that generator as they were.

        Raises:
            ValueError: Where the entries of `weights` differ from the
                        network's, as a checkpoint another agent wrote holds
                        them.
        """
        with fork_rng(devices=[]):
            network = acting_network(
                self.envs.single_action_space.n,
                self.algorithm,
                self.envs.single_observation_space
            )

        with matching_networks():
            network.load_state_dict(weights.online)

        return Evaluation(
            goal     = self.goal,
            outcomes = self.play(
                Policy(
                    device  = self.device,
                    epsilon = 0.0 if self.algorithm.sampled else self.settings.epsilon,
                    network = network.to(self.device)
                )
            ),
            step = weights.step
        )

    def play(self, policy: Policy) -> list[Outcome]:
        """
        Plays the settings' `episodes` of `policy`, starting each in
        the first environment to come free under the seeds `seeds` draws
        for its number. Once every episode has started, an environment
        coming free plays on through the numbers past them and discards
        each, since `step` steps every environment at once and, under
        `AutoresetMode.DISABLED`, steps one past its episode's end unless
        `play` resets it.

        Returns:
            What each episode reached, in the order of their numbers.
        """
        numbers  = count()
        playing  = [next(numbers) for _ in range(self.envs.num_envs)]
        spaces   = [deepcopy(self.envs.single_action_space) for _ in playing]
        ended    = ones(len(playing), bool)
        outcomes = {}

        while len(outcomes) < self.settings.episodes:
            if ended.any():
                for slot in flatnonzero(ended):
                    spaces[slot].seed(self.seeds(playing[slot])[1])

                observations, _ = self.envs.reset(
                    options = {"reset_mask": ended},
                    seed    = [self.seeds(number)[0] for number in playing]
                )

            observations, _, terminated, truncated, info = self.envs.step(
                policy.act(observations, spaces)
            )
            ended = terminated | truncated

            for slot in flatnonzero(ended):
                if playing[slot] < self.settings.episodes:
                    outcomes[playing[slot]] = info["outcome"][slot]

                playing[slot] = next(numbers)

        return [outcomes[number] for number in range(self.settings.episodes)]

    def seeds(self, number: int) -> list[int]:
        """
        Draws the seeds episode `number` starts from, its reset's and
        then its action space's, from the child of the evaluation stream's
        `SeedSequence` that the number names.
        """
        return (
            SeedSequence(self.seed, spawn_key=(number,))
            .generate_state(2, uint64)
            .tolist()
        )
