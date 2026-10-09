"""
Defines `Agent`, the deep Q-network agent, which chooses each action, stores
each transition in replay memory, and trains its online network on batches
drawn from it, counting every schedule in environment steps.
"""

from copy                import deepcopy
from numpy               import interp, ndarray
from numpy.random        import default_rng
from torch               import as_tensor, default_generator, inference_mode
from torch.nn.functional import huber_loss
from torch.nn.utils      import clip_grad_norm_
from torch.optim         import Adam
from torch.random        import fork_rng

from squirtl.agent.networks import QNetwork
from squirtl.agent.replay   import Replay
from squirtl.agent.schemas  import AgentSettings, Checkpoint


class Agent:
    """
    A deep Q-network agent after Mnih et al., choosing each action
    epsilon-greedily from its online network and training that network
    toward targets its target network values, with the target network a copy
    of the online network every `sync_steps` steps.
    """

    def __init__(
        self,
        actions  : int,
        seed     : int,
        settings : AgentSettings,
        shape    : tuple[int, ...],
        steps    : int
    ):
        """
        Builds both networks for `actions` actions over an observation of
        `shape`, Adam over the online network, and empty replay memory, for
        a run of `steps` environment steps.

        Args:
            seed: The seed the online network's weights, the draws choosing
                  a random action, and the draws sampling replay memory each
                  start from, a 64-bit unsigned integer.
        """
        self.exploration, sampling = default_rng(seed).spawn(2)

        with fork_rng(devices=[]):
            default_generator.manual_seed(seed)
            self.online = QNetwork(actions, shape).to(settings.device)

        self.actions   = actions
        self.optimizer = Adam(self.online.parameters(), lr=settings.learning_rate)
        self.replay    = Replay(settings.capacity, sampling, shape)
        self.settings  = settings
        self.step      = 0
        self.steps     = steps
        self.target    = deepcopy(self.online).requires_grad_(False)

    @property
    def checkpoint(self) -> Checkpoint:
        """
        Gathers the state a resumed run continues training from, whose
        tensors are the networks' and the optimizer's own rather than
        copies, so it holds the values they carry when it is saved.
        """
        return Checkpoint(
            exploration = self.exploration.bit_generator.state,
            online      = self.online.state_dict(),
            optimizer   = self.optimizer.state_dict(),
            sampling    = self.replay.generator.bit_generator.state,
            step        = self.step,
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

    @inference_mode()
    def act(self, observation: ndarray) -> int:
        """
        Chooses a random action with probability `epsilon`, and otherwise
        the action the online network values highest for `observation`,
        which it evaluates without building an autograd graph.
        """
        if self.exploration.random() < self.epsilon:
            return self.exploration.integers(self.actions).item()

        return (
            self.online(as_tensor(observation, device=self.settings.device)[None])
                .argmax()
                .item()
        )

    def begin(self, observation: ndarray):
        """
        Stores the reset observation of the episode starting.
        """
        self.replay.begin(observation)

    def remember(
        self,
        action      : int,
        observation : ndarray,
        reward      : float,
        terminated  : bool
    ):
        """
        Stores the transition `action` made, which reached `observation`,
        earned `reward`, and `terminated` the episode or not, as one
        environment step. Copies the online network into the target network
        on every step that `sync_steps` divides.
        """
        self.replay.store(action, observation, reward, terminated)
        self.step += 1

        if self.step % self.settings.sync_steps == 0:
            self.target.load_state_dict(self.online.state_dict())

    def restore(self, checkpoint: Checkpoint):
        """
        Loads `checkpoint` into both networks, the optimizer, the step
        count, and both generators, in place, so the optimizer keeps
        stepping the parameters of the network the checkpoint loads into.
        """
        self.exploration.bit_generator.state      = checkpoint.exploration
        self.replay.generator.bit_generator.state = checkpoint.sampling
        self.step = checkpoint.step
        self.online.load_state_dict(checkpoint.online)
        self.optimizer.load_state_dict(checkpoint.optimizer)
        self.target.load_state_dict(checkpoint.target)

    def update(self):
        """
        Takes one gradient step on the Huber loss between the values the
        online network gives a batch drawn from replay memory and the
        targets the target network gives it, clipping the gradient's norm at
        `max_grad_norm` before the step, and takes none while replay memory
        holds fewer transitions than `batch_size`.
        """
        if len(self.replay) < self.settings.batch_size:
            return

        batch = self.replay.sample(self.settings.device, self.settings.batch_size)
        loss  = huber_loss(
            batch.values(self.online),
            batch.targets(self.settings.discount, self.target)
        )

        self.optimizer.zero_grad()
        loss.backward()
        clip_grad_norm_(self.online.parameters(), self.settings.max_grad_norm)
        self.optimizer.step()
