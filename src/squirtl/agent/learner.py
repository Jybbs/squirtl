"""
Defines `Agent`, the deep Q-network agent, which chooses each action, stores
each transition in replay memory, and trains its online network on batches
drawn from it, counting every schedule in environment steps.
"""

from collections.abc     import Mapping
from copy                import deepcopy
from gymnasium.spaces    import Dict
from numpy               import interp, ndarray
from numpy.random        import default_rng
from torch               import as_tensor, default_generator, inference_mode, set_num_threads
from torch.backends      import nnpack
from torch.nn.functional import huber_loss
from torch.nn.utils      import clip_grad_norm_
from torch.optim         import Adam
from torch.random        import fork_rng

from squirtl.agent.networks import QNetwork
from squirtl.agent.replay   import Replay
from squirtl.agent.schemas  import AgentSettings, Checkpoint, Update, Weights


class Agent:
    """
    A deep Q-network agent after Mnih et al., choosing each action
    epsilon-greedily from its online network and training that network
    every `update_steps` steps after a warm-up of `warmup_steps`, toward the
    Double DQN targets of van Hasselt et al. where `double_q` is set. Its
    target network is a copy of the online network every `sync_steps` steps.
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
        Builds both networks for `actions` actions over `space`, Adam over
        the online network, and empty replay memory for a run of `steps`
        steps. Before building them, it turns NNPACK off for the whole
        process and sets the process's thread count to the `threads` the
        settings name, where they name one.

        Args:
            seed: The unsigned 64-bit seed the weights, the random actions,
                  and the replay draws each start from.
        """
        # NNPACK runs this network's convolutions on the CPU slower than PyTorch's own.
        nnpack.set_flags(False)

        if settings.threads:
            set_num_threads(settings.threads)

        self.exploration, sampling = default_rng(seed).spawn(2)

        with fork_rng(devices=[]):
            default_generator.manual_seed(seed)
            self.online = QNetwork(actions, space).to(settings.device)

        self.actions   = actions
        self.optimizer = Adam(self.online.parameters(), lr=settings.learning_rate)
        self.replay    = Replay(settings.capacity, sampling, space)
        self.settings  = settings
        self.step      = 0
        self.steps     = steps
        self.target    = deepcopy(self.online).requires_grad_(False)

    @property
    def checkpoint(self) -> Checkpoint:
        """
        Gathers the state a resumed run continues training from, holding
        the networks' own `state_dict`s, the optimizer's tensors, and replay
        memory's arrays uncopied.
        """
        return Checkpoint(
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
        Reads the chance of a random action at the current step, falling
        linearly from `epsilon_start` to `epsilon_end` over the first
        `exploration_fraction` of the run's steps and holding there.
        """
        return interp(
            self.step,
            [0, self.settings.exploration_fraction * self.steps],
            [self.settings.epsilon_start, self.settings.epsilon_end]
        )

    @property
    def weights(self) -> Weights:
        """
        Gathers the online network's `state_dict`, uncopied, beside the step
        it has reached, which an evaluation plays from.
        """
        return Weights(online=self.online.state_dict(), step=self.step)

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
            self.online(
                {
                    key: as_tensor(stack, device=self.settings.device)[None]
                    for key, stack in observation.items()
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
            self.target.load_state_dict(self.online.state_dict())

    def restore(self, checkpoint: Checkpoint):
        """
        Loads `checkpoint` into replay memory, both networks, the optimizer,
        the step count, and both generators, the networks in place, so
        the optimizer keeps stepping the parameters of the network the
        checkpoint loads into.

        Raises:
            ValueError: Where replay memory's arrays or a network's entries
                        differ from the agent's, as a checkpoint another
                        agent wrote holds them.
        """
        self.replay.load(checkpoint.replay)

        try:
            self.online.load_state_dict(checkpoint.online)
            self.target.load_state_dict(checkpoint.target)
        except RuntimeError as error:
            # `load_state_dict` raises `RuntimeError` on an entry one side lacks or the
            # network holds at another shape.
            raise ValueError(
                f"the checkpoint's networks differ from the agent's: {error}"
            ) from error

        self.exploration.bit_generator.state      = checkpoint.exploration
        self.replay.generator.bit_generator.state = checkpoint.sampling
        self.step = checkpoint.step
        self.optimizer.load_state_dict(checkpoint.optimizer)

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
        values = batch.values(self.online)
        loss   = huber_loss(
            values,
            batch.targets(
                self.online if settings.double_q else self.target,
                settings.discount,
                self.target
            )
        )

        self.optimizer.zero_grad()
        loss.backward()
        clip_grad_norm_(self.online.parameters(), settings.max_grad_norm)
        self.optimizer.step()

        return Update(loss=loss.item(), value=values.mean().item())
