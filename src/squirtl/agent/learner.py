"""
Defines the agents a run trains, each choosing each action and training its
network, counting every schedule in environment steps:

- `Learner`, the base of every agent, holding the network it acts through,
  its optimizer, and the step it has reached
- `DQN`, the deep Q-network, which stores each transition in replay memory
  and trains on batches drawn from it
- `PQN` and `PPO`, which act across environments run in parallel and train
  on each `Rollout` they collect, as `RolloutAgent` sets out
"""

from abc                 import ABC, abstractmethod
from collections.abc     import Iterator, Mapping
from contextlib          import contextmanager
from copy                import deepcopy
from gymnasium.spaces    import Dict
from numpy               import array_split, interp, ndarray, take_along_axis, where
from numpy.random        import default_rng
from torch               import Tensor, as_tensor, inference_mode, maximum, minimum, stack
from torch.distributions import Categorical
from torch.nn.functional import huber_loss, mse_loss
from torch.nn.utils      import clip_grad_norm_
from torch.optim         import Adam, AdamW, Optimizer, RAdam
from typing              import ClassVar

from squirtl.agent.checkpoint import Checkpoint, ReplayCheckpoint, RolloutCheckpoint, Weights
from squirtl.agent.networks   import seeded_network, tensors
from squirtl.agent.replay     import Replay
from squirtl.agent.rollout    import Rollout
from squirtl.agent.schemas    import AgentSettings, Algorithm, Measures, PPOSettings, PQNSettings, Update


class Learner[C: Checkpoint](ABC):
    """
    The base of every agent a run trains, which acts through one network
    seeded from the agent's stream, steps it with its `optimizer_class`,
    and counts the environment steps it has taken toward a run of `steps`.
    A checkpoint of kind `C` carries the network, the optimizer, and that
    count over to a resumed run.
    """

    optimizer_class: ClassVar[type[Optimizer]]
    """
    The optimizer the agent trains its network with.
    """

    def __init__(
        self,
        actions  : int,
        seed     : int,
        settings : AgentSettings,
        space    : Dict,
        steps    : int
    ):
        """
        Builds the network for `actions` actions over `space` and its
        optimizer at the `learning_rate` of `hyperparameters`, for a run of
        `steps` steps.

        Args:
            seed: The unsigned 64-bit seed the weights start from.
        """
        self.actions   = actions
        self.network   = seeded_network(actions, seed, settings, space)
        self.settings  = settings
        self.step      = 0
        self.steps     = steps
        self.optimizer = self.optimizer_class(
            self.network.parameters(),
            lr = self.hyperparameters.learning_rate
        )

    @property
    @abstractmethod
    def checkpoint(self) -> C:
        """
        Gathers the state a resumed run continues training from on the
        agent's side, holding each `state_dict` and the optimizer's tensors
        uncopied.
        """

    @property
    @abstractmethod
    def epsilon(self) -> float | None:
        """
        Reads the chance of a random action at the current step, or `None`
        for an agent sampling each action from its policy.
        """

    @property
    def hyperparameters(self) -> AgentSettings | PPOSettings | PQNSettings:
        """
        Reads the record holding the learning rate and the gradient's
        clipping norm the agent trains under, the record of the settings
        PQN or PPO alone reads, or the settings themselves for the deep
        Q-network, whose own sit on them.
        """
        return self.settings.hyperparameters or self.settings

    @property
    def weights(self) -> Weights:
        """
        Gathers the network's `state_dict`, uncopied, beside the step it has
        reached, which an evaluation plays from.
        """
        return Weights(online=self.network.state_dict(), step=self.step)

    def annealed(self, schedule: AgentSettings | PQNSettings) -> float:
        """
        Reads the chance of a random action at the current step, falling
        linearly from the `epsilon_start` of `schedule` to its `epsilon_end`
        over the first `exploration_fraction` of the run's steps and holding
        there.
        """
        return interp(
            self.step,
            [0, schedule.exploration_fraction * self.steps],
            [schedule.epsilon_start, schedule.epsilon_end]
        )

    def descend(self, loss: Tensor):
        """
        Takes one gradient step on `loss`, its gradient's norm clipped at
        the `max_grad_norm` of `hyperparameters`.
        """
        self.optimizer.zero_grad()
        loss.backward()
        clip_grad_norm_(self.network.parameters(), self.hyperparameters.max_grad_norm)
        self.optimizer.step()

    def restore(self, checkpoint: C):
        """
        Loads `checkpoint` into the network in place, the step count, and
        the optimizer, so the optimizer keeps stepping the parameters of the
        network the checkpoint loads into.

        Raises:
            ValueError: Where the network's entries differ from the agent's,
                        as a checkpoint another agent wrote holds them.
        """
        with matching_networks():
            self.network.load_state_dict(checkpoint.online)

        self.step = checkpoint.step
        self.optimizer.load_state_dict(checkpoint.optimizer)


class DQN(Learner[ReplayCheckpoint]):
    """
    The deep Q-network after Mnih et al., choosing each action
    epsilon-greedily from its online network, held as `network`,
    and training it every `update_steps` steps after a warm-up of
    `warmup_steps`, toward the Double DQN targets of van Hasselt et al.
    where `double_q` is set. Its target network is a copy of the online
    network every `sync_steps` steps.
    """

    optimizer_class = Adam

    def __init__(
        self,
        actions  : int,
        seed     : int,
        settings : AgentSettings,
        space    : Dict,
        steps    : int
    ):
        """
        Builds the online network and Adam over it as `Learner` does, beside
        the target network and empty replay memory.

        Args:
            seed: The unsigned 64-bit seed the weights, the random actions,
                  and the replay draws each start from.
        """
        super().__init__(actions, seed, settings, space, steps)

        self.exploration, sampling = default_rng(seed).spawn(2)

        self.replay = Replay(settings.capacity, sampling, space)
        self.target = deepcopy(self.network).requires_grad_(False)

    @property
    def checkpoint(self) -> ReplayCheckpoint:
        """
        Gathers the state a resumed run continues training from, holding
        the networks' own `state_dict`s, the optimizer's tensors, and replay
        memory's arrays uncopied.
        """
        return ReplayCheckpoint(
            **dict(self.weights),
            exploration = self.exploration.bit_generator.state,
            optimizer   = self.optimizer.state_dict(),
            replay      = self.replay.arrays,
            sampling    = self.replay.generator.bit_generator.state,
            target      = self.target.state_dict()
        )

    @property
    def epsilon(self) -> float:
        """
        Reads the chance of a random action at the current step.
        """
        return self.annealed(self.settings)

    @inference_mode()
    def act(self, observation: Mapping[str, ndarray]) -> int:
        """
        Chooses a random action with probability `epsilon`, and otherwise
        the action the online network values highest for `observation`,
        which it evaluates without building an autograd graph.
        """
        if self.exploration.random() < self.epsilon:
            return self.exploration.integers(self.actions).item()

        return (
            self.network(
                {
                    key: entry[None]
                    for key, entry in tensors(self.settings.device, observation).items()
                }
            )
                .argmax()
                .item()
        )

    def begin(self, observation: Mapping[str, ndarray]):
        """
        Stores the reset observation of the episode starting.
        """
        self.replay.begin(observation)

    def remember(
        self,
        action      : int,
        observation : Mapping[str, ndarray],
        reward      : float,
        terminated  : bool
    ):
        """
        Stores the transition `action` made as one environment step,
        copying the online network into the target on each step `sync_steps`
        divides.
        """
        self.replay.store(action, observation, reward, terminated)
        self.step += 1

        if self.step % self.settings.sync_steps == 0:
            self.target.load_state_dict(self.network.state_dict())

    def restore(self, checkpoint: ReplayCheckpoint):
        """
        Loads `checkpoint` into replay memory and the target network
        in place, then into the online network, the step count, and the
        optimizer as `Learner` does, and into both generators.

        Raises:
            ValueError: Where replay memory's arrays or a network's entries
                        differ from the agent's, as a checkpoint another
                        agent wrote holds them.
        """
        self.replay.load(checkpoint.replay)

        with matching_networks():
            self.target.load_state_dict(checkpoint.target)

        super().restore(checkpoint)

        self.exploration.bit_generator.state      = checkpoint.exploration
        self.replay.generator.bit_generator.state = checkpoint.sampling

    def update(self) -> Update | None:
        """
        Takes one gradient step on the Huber loss between the online
        network's values for a batch and the targets the target network
        values, under the action the online network chooses where `double_q`
        is set, its gradient's norm clipped at `max_grad_norm`. It takes one
        on each environment step `update_steps` divides once the agent has
        remembered `warmup_steps` steps, and none on any other.

        Returns:
            The loss and the mean value the step read, or `None` on an
            environment step that takes none.
        """
        settings = self.settings

        if self.step < settings.warmup_steps or self.step % settings.update_steps:
            return None

        batch  = self.replay.sample(settings.device, settings.batch_size)
        values = batch.values(self.network)
        loss   = huber_loss(
            values,
            batch.targets(
                self.network if settings.double_q else self.target,
                settings.discount,
                self.target
            )
        )

        self.descend(loss)

        return Update(loss=loss.item(), value=values.mean().item())


@contextmanager
def matching_networks() -> Iterator[None]:
    """
    Raises each `RuntimeError` the block raises as a `ValueError`, since
    `load_state_dict` raises the former on an entry one side lacks or the
    network holds at another shape.

    Raises:
        ValueError: Where a network's entries differ from the agent's, as a
                    checkpoint another agent wrote holds them.
    """
    try:
        yield
    except RuntimeError as error:
        raise ValueError(
            f"the checkpoint's networks differ from the agent's: {error}"
        ) from error


class RolloutAgent(Learner[RolloutCheckpoint]):
    """
    An agent acting across environments run in parallel, which stores each
    step of every environment in its `Rollout` and, once the rollout fills,
    trains its network for `epochs` passes over it, each pass split into
    `minibatches` drawn in an order its generator shuffles. Every random
    draw it makes comes from that generator, seeded from the agent's stream.
    """

    def __init__(
        self,
        actions      : int,
        environments : int,
        seed         : int,
        settings     : AgentSettings,
        space        : Dict,
        steps        : int
    ):
        """
        Builds the network and its optimizer as `Learner` does, and a
        rollout of `environments` columns.

        Args:
            seed: The unsigned 64-bit seed the weights and the generator
                  each start from.
        """
        super().__init__(actions, seed, settings, space, steps)

        self.generator = default_rng(seed)
        self.rollout   = Rollout(
            environments,
            space,
            self.hyperparameters.rollout_steps
        )

    @property
    def checkpoint(self) -> RolloutCheckpoint:
        """
        Gathers the state a resumed run continues training from on the
        agent's side, holding the network's own `state_dict` and the
        optimizer's tensors uncopied.
        """
        return RolloutCheckpoint(
            **dict(self.weights),
            generator = self.generator.bit_generator.state,
            optimizer = self.optimizer.state_dict()
        )

    @inference_mode()
    def act(self, observations: Mapping[str, ndarray]) -> ndarray:
        """
        Chooses each environment's action from the batch of `observations`
        through `choose`, which it evaluates without building an autograd
        graph, and stores the step's observations, actions, and values in
        the rollout.

        Returns:
            One action per environment, a `(environments,)` array of
            `int64`.
        """
        actions, values, log_probs = self.choose(
            tensors(self.settings.device, observations)
        )
        self.rollout.store_action(
            actions      = actions,
            log_probs    = log_probs,
            observations = observations,
            values       = values
        )

        return actions

    @abstractmethod
    def choose(self, observations: Mapping[str, Tensor]) -> tuple[ndarray, ndarray, ndarray | None]:
        """
        Chooses each environment's action for the batch of `observations`.

        Returns:
            The actions, the value of each observation, and, for PPO, each
            action's log-probability.
        """

    @abstractmethod
    def learn(self, batch: Mapping[str, Tensor]) -> tuple[Tensor, Tensor]:
        """
        Computes the loss on one minibatch of the rollout.

        Returns:
            The loss beside a tensor of the measures the agent reads on the
            minibatch, in the order its `Measures` declares them.
        """

    @staticmethod
    def named(algorithm: Algorithm) -> type[RolloutAgent]:
        """
        Reads the class of the agent `algorithm` names.
        """
        return {Algorithm.PPO: PPO, Algorithm.PQN: PQN}[algorithm]

    def remember(
        self,
        bootstraps : ndarray,
        rewards    : ndarray,
        terminated : ndarray,
        truncated  : ndarray
    ):
        """
        Stores the outcome of the step every environment just took, which
        counts as one environment step apiece.
        """
        self.rollout.store_outcome(
            bootstraps = bootstraps,
            rewards    = rewards,
            terminated = terminated,
            truncated  = truncated
        )
        self.step += len(rewards)

    def restore(self, checkpoint: RolloutCheckpoint):
        """
        Loads `checkpoint` into the network, the step count, and the
        optimizer as `Learner` does, and into the generator.

        Raises:
            ValueError: Where the network's entries differ from the agent's,
                        as a checkpoint another agent wrote holds them.
        """
        super().restore(checkpoint)

        self.generator.bit_generator.state = checkpoint.generator

    def update(self, observations: Mapping[str, ndarray]) -> Measures:
        """
        Trains the network on the rollout toward the λ-returns that
        `Rollout.returns` computes from the value of `observations`, the
        observation each environment reached, taking one gradient step per
        minibatch with its gradient's norm clipped at `max_grad_norm`, and
        empties the rollout.

        Returns:
            The update's measures, each averaged over its minibatches.
        """
        hyperparameters = self.hyperparameters
        rollout         = self.rollout
        batch           = rollout.batch(
            self.settings.device,
            rollout.returns(
                hyperparameters.trace_decay,
                self.settings.discount,
                self.value(observations)
            )
        )
        measured = []

        for _ in range(hyperparameters.epochs):
            for indices in array_split(
                self.generator.permutation(len(batch["actions"])),
                hyperparameters.minibatches
            ):
                selected       = as_tensor(indices, device=self.settings.device)
                loss, measures = self.learn(
                    {name: tensor[selected] for name, tensor in batch.items()}
                )

                self.descend(loss)
                measured.append(measures)

        rollout.row = 0

        return self.settings.algorithm.measures.averaged(
            len(measured),
            stack(measured).sum(0).tolist()
        )

    @abstractmethod
    def value(self, observations: Mapping[str, ndarray]) -> ndarray:
        """
        Values each of a batch of `observations`, without building an
        autograd graph.

        Returns:
            A `(batch,)` array of `float32`.
        """


class PPO(RolloutAgent):
    """
    Proximal policy optimization after Schulman et al., sampling each
    action from its policy and training toward the clipped objective with
    the value's clipped loss Pleines et al. train with on Pokémon Red, the
    advantages normalized over each minibatch as CleanRL's `ppo_atari.py`
    normalizes them.
    """

    optimizer_class = AdamW

    @property
    def epsilon(self):
        """
        Reads no chance of a random action, since PPO samples each action
        from its policy.
        """
        return None

    def choose(
        self,
        observations: Mapping[str, Tensor]
    ) -> tuple[ndarray, ndarray, ndarray]:
        """
        Samples each action from the policy's logits through the Gumbel-max
        trick, adding Gumbel noise the generator draws to each action's
        log-probability and taking the largest.
        """
        logits, values = self.network.heads(observations)
        log_probs      = logits.log_softmax(1).numpy(force=True)
        actions = (log_probs + self.generator.gumbel(size=log_probs.shape)).argmax(1)

        return (
            actions,
            values.numpy(force=True),
            take_along_axis(log_probs, actions[:, None], 1)[:, 0]
        )

    def learn(self, batch: Mapping[str, Tensor]) -> tuple[Tensor, Tensor]:
        """
        Computes Schulman et al.'s clipped objective on the minibatch beside
        the value's loss, the larger of its squared error and the squared
        error of the value clipped to within `clip_range` of the old one, as
        Pleines et al. clip it, weighted by `value_coefficient`.
        """
        ppo            = self.settings.ppo
        logits, values = self.network.heads(batch)
        policy         = Categorical(logits=logits)
        log_ratio      = policy.log_prob(batch["actions"]) - batch["log_probs"]
        ratio          = log_ratio.exp()
        advantages     = batch["returns"] - batch["values"]

        # CleanRL's `ppo_atari.py` adds `1e-8`, which keeps equal advantages finite.
        advantages  = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        policy_loss = -minimum(
            ratio * advantages,
            ratio.clamp(1 - ppo.clip_range, 1 + ppo.clip_range) * advantages
        ).mean()
        value_loss = maximum(
            (values - batch["returns"]) ** 2,
            (
                batch["values"]
                + (values - batch["values"]).clamp(-ppo.clip_range, ppo.clip_range)
                - batch["returns"]
            )
            ** 2
        ).mean()

        return policy_loss + ppo.value_coefficient * value_loss, stack(
            [
                ((ratio - 1).abs() > ppo.clip_range).float().mean(),
                policy.entropy().mean(),
                (ratio - 1 - log_ratio).mean(),
                policy_loss, value_loss
            ]
        ).detach()

    @inference_mode()
    def value(self, observations: Mapping[str, ndarray]) -> ndarray:
        """
        Reads the critic's value of each observation.
        """
        return (
            self.network.heads(tensors(self.settings.device, observations))[1]
                .numpy(force=True)
        )


class PQN(RolloutAgent):
    """
    Gallici et al.'s parallel Q-network, choosing each action
    epsilon-greedily from its layer-normalized Q-network and training it
    on half the squared error between its values and the λ-returns, with
    neither a target network nor replay memory.
    """

    optimizer_class = RAdam

    @property
    def epsilon(self) -> float:
        """
        Reads the chance of a random action at the current step.
        """
        return self.annealed(self.settings.pqn)

    def choose(
        self,
        observations: Mapping[str, Tensor]
    ) -> tuple[ndarray, ndarray, None]:
        """
        Takes a random action in each environment where a draw of the
        generator falls below `epsilon`, and otherwise the action the
        network values highest, drawing both a chance and a random action
        for every environment, so each step draws alike whatever `epsilon`
        holds.
        """
        values  = self.network(observations).numpy(force=True)
        explore = self.generator.random(len(values)) < self.epsilon
        random  = self.generator.integers(self.actions, size=len(values))

        return where(explore, random, values.argmax(1)), values.max(1), None

    def learn(self, batch: Mapping[str, Tensor]) -> tuple[Tensor, Tensor]:
        """
        Computes half the squared error between the network's value of each
        sampled action and its λ-return, as Gallici et al. train.
        """
        values = self.network(batch).gather(1, batch["actions"][:, None])[:, 0]
        loss   = mse_loss(values, batch["returns"]) / 2

        return loss, stack([loss, values.mean()]).detach()

    @inference_mode()
    def value(self, observations: Mapping[str, ndarray]) -> ndarray:
        """
        Reads the highest value the network gives each observation.
        """
        return (
            self.network(tensors(self.settings.device, observations))
                .amax(1)
                .numpy(force=True)
        )

