"""
Defines `Evaluator`, which plays an evaluation's episodes across the
environments `gymnasium.make_vec` runs in parallel, and `Policy`, the policy
it plays, epsilon-greedy or sampled from a network's logits.
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
    The policy an evaluation plays, which chooses each action in one of
    three ways:

    - A random action at every step, where it holds no `network`
    - An action drawn from the softmax of the logits of PPO's policy, where
      `sampled` holds
    - Otherwise a random action with probability `epsilon` and the action
      `network` scores highest the rest of the time, the highest value of a
      Q-network or the largest logit of PPO's policy

    Each environment's random draws come from that environment's own action
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

    sampled: bool = False
    """
    Whether each action is drawn from the softmax of the network's scores,
    PPO's policy, in place of the epsilon-greedy choice.
    """

    @inference_mode()
    def act(self, observations: Mapping[str, ndarray], spaces: Sequence[Discrete]) -> ndarray:
        """
        Chooses each environment's action from the batch of `observations`,
        which the network scores without building an autograd graph.

        - Without a network, samples each action from its space in `spaces`
        - Where `sampled` holds, takes the largest of each logit plus Gumbel
          noise that space's generator draws, which samples an action from the
          softmax of the logits as PPO's training does
        - Otherwise samples an action from each space and then draws from its
          generator whether to keep it or take the action the network scores
          highest

        Returns:
            One action per environment, a `(len(spaces),)` array of `int64`.
        """
        if self.network is None:
            return array([space.sample() for space in spaces])

        scores = self.network(tensors(self.device, observations))

        if self.sampled:
            noise = array([space.np_random.gumbel(size=space.n) for space in spaces])

            return (scores.numpy(force=True) + noise).argmax(1)

        actions = array([space.sample() for space in spaces])
        explore = array([space.np_random.random() < self.epsilon for space in spaces])

        return where(explore, actions, scores.argmax(1).numpy(force=True))


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
        Closes the environments and the processes running them, terminating
        the workers where the `with` block raised. Without `terminate`,
        `AsyncVectorEnv.close` calls `step_wait` again to finish a pending
        step. An interrupt raised inside `step_wait` leaves some of the
        workers' pipes already read, so that call blocks forever on a pipe
        no worker writes to again.
        """
        self.envs.close(terminate=any(raised))

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

    @property
    def digest(self) -> str:
        """
        Reads the first environment's `digest`, the digest of the state its
        intro left, which every environment shares.
        """
        return self.envs.get_attr("digest")[0]

    def baseline(self) -> Evaluation:
        """
        Plays the random baseline's episodes, every action sampled from the
        seeded action space.
        """
        return Evaluation(
            argmax   = None,
            goal     = self.goal,
            outcomes = self.play(Policy()),
            step     = None
        )

    def evaluate(self, weights: Weights) -> Evaluation:
        """
        Plays the episodes of the agent's network holding `weights`, at
        their step, epsilon-greedily for the deep Q-network and PQN, and
        for PPO sampling each action from its policy, as Schulman et al.
        score PPO, and again taking its most likely action at every step, as
        Mhammedi and Cohan play the rollouts choosing their best checkpoint
        and as Stable-Baselines3's `evaluate_policy` plays by default. The
        network is built anew, under a fork of PyTorch's global generator,
        so the evaluation leaves the agent and that generator as they were.

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

        sampled = self.algorithm.sampled
        policy  = Policy(
            device  = self.device,
            epsilon = 0.0 if sampled else self.settings.epsilon,
            network = network.to(self.device),
            sampled = sampled
        )

        return Evaluation(
            argmax = self.play(
                policy.model_copy(update={"sampled": False})
            ) if sampled else None,
            goal     = self.goal,
            outcomes = self.play(policy),
            step     = weights.step
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
