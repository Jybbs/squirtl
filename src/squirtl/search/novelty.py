"""
Defines `Novelty`, the random network distillation of Burda et al. that
scores how uncertain a search is of a frame stack, as Appendix A.3 of
Mhammedi and Cohan's "Decoupling Exploration and Policy Optimization" sets
it out.
"""

from collections.abc          import Iterable, Mapping
from gymnasium.spaces         import Box, Dict
from gymnasium.wrappers.utils import RunningMeanStd
from math                import sqrt
from numpy               import array, asarray, frombuffer, ndarray, uint8
from numpy.random        import Generator
from statistics          import fmean
from torch               import Tensor, as_tensor, default_generator, float32, inference_mode, zeros
from torch.nn            import Conv2d, LazyLinear, Linear, ReLU, Sequential
from torch.nn.functional import mse_loss
from torch.nn.init       import orthogonal_, zeros_
from torch.optim         import Adam
from torch.random        import fork_rng

from squirtl.agent.networks      import QNetwork
from squirtl.agent.replay        import Replay
from squirtl.agent.schemas       import AgentSettings
from squirtl.environment.schemas import Entry, Snapshot
from squirtl.search.schemas      import SearchSettings


class Novelty:
    """
    A fixed random target network and the predictor trained toward it, whose
    squared error on a frame stack falls the more often replay memory has
    held stacks like it. Each network reads a `(depth, height, width)` stack
    normalized by the running mean and standard deviation of each pixel and
    clipped to `[-5, 5]`.
    """

    def __init__(
        self,
        agent    : AgentSettings,
        sampling : Generator,
        seed     : int,
        settings : SearchSettings,
        space    : Box
    ):
        """
        Builds both networks over the frame stacks `space` declares, on the
        device and threads `agent` names, Adam over the predictor, and empty
        replay memory drawing every batch from `sampling`.

        Args:
            seed: The unsigned 64-bit seed both networks' weights start
                  from.
        """
        agent.configure()

        with fork_rng(devices=[]):
            default_generator.manual_seed(seed)
            self.predictor = self.network(space.shape).to(agent.device)
            self.target    = (
                self.network(space.shape)
                    .to(agent.device)
                    .requires_grad_(False)
            )

        self.device     = agent.device
        self.normalizer = RunningMeanStd(shape=space.shape[1:])
        self.optimizer  = Adam(self.predictor.parameters(), lr=settings.learning_rate)
        self.replay   = Replay(settings.capacity, sampling, Dict({Entry.FRAMES: space}))
        self.settings = settings
        self.shape    = space.shape
        self.updates  = 0

    @property
    def arrays(self) -> dict[str, ndarray]:
        """
        Gathers the running mean, variance, and count beside each array of
        replay memory, uncopied, under its name.
        """
        return self.replay.arrays | {
            "count" : asarray(self.normalizer.count),
            "mean"  : self.normalizer.mean,
            "var"   : self.normalizer.var
        }

    @property
    def networks(self) -> dict[str, object]:
        """
        Gathers each `state_dict`, the updates taken, and the state of
        the generator drawing each batch, uncopied, which a resumed search
        continues training from.
        """
        return {
            "optimizer" : self.optimizer.state_dict(),
            "predictor" : self.predictor.state_dict(),
            "sampling"  : self.replay.generator.bit_generator.state,
            "target"    : self.target.state_dict(),
            "updates"   : self.updates
        }

    def error(self, frames: Tensor) -> Tensor:
        """
        Measures the predictor's squared error against the target on each
        stack of `frames`, a `(batch, depth, height, width)` tensor of
        `uint8`, after normalizing each pixel and clipping it.

        Returns:
            A `(batch,)` tensor.
        """
        mean, deviation = (
            as_tensor(values, device=self.device, dtype=float32)
            for values in (self.normalizer.mean, self.normalizer.var ** 0.5)
        )
        inputs = ((frames.to(float32) - mean) / deviation).clamp(-5, 5)

        return mse_loss(
            self.predictor(inputs),
            self.target(inputs),
            reduction = "none"
        ).mean(1)

    def load(self, arrays: Mapping[str, ndarray], networks: Mapping[str, object]):
        """
        Loads what `arrays` and `networks` hold, as `arrays` and `networks`
        gather them, the networks in place, so the optimizer keeps stepping
        the parameters of the predictor it holds.

        Raises:
            ValueError: Where replay memory's arrays or a network's entries
                        differ from those this search builds.
        """
        self.replay.load({name: arrays[name] for name in self.replay.arrays})

        try:
            self.predictor.load_state_dict(networks["predictor"])
            self.target.load_state_dict(networks["target"])
        except RuntimeError as error:
            # `load_state_dict` raises `RuntimeError` on an entry one side lacks or the
            # network holds at another shape.
            raise ValueError(
                f"the checkpoint's networks differ from the search's: {error}"
            ) from error

        self.normalizer.count = arrays["count"].item()
        self.normalizer.mean  = arrays["mean"]
        self.normalizer.var   = arrays["var"]
        self.optimizer.load_state_dict(networks["optimizer"])
        self.replay.generator.bit_generator.state = networks["sampling"]
        self.updates = networks["updates"]

    @staticmethod
    def network(shape: tuple[int, int, int]) -> Sequential:
        """
        Builds the convolutions `QNetwork.encoder` builds for an image entry
        beneath the appendix's head, two 1024-unit linear layers separated
        by a ReLU. An observation of zeros sets each lazy layer's depth and
        width, and the convolutions take the orthogonal weights at a gain of
        the square root of 2 and the zero biases of Burda et al.'s `conv`.
        """
        network = Sequential(
            QNetwork.encoder(shape),
            LazyLinear(1024),
            ReLU(),
            Linear(1024, 1024)
        )
        network(zeros(1, *shape))

        for module in network[0]:
            if isinstance(module, Conv2d):
                orthogonal_(module.weight, sqrt(2))
                zeros_(module.bias)

        return network

    def observe(self, frames: bytes, start: Snapshot):
        """
        Stores the stack `start` holds and each newest frame in `frames`
        after it in replay memory, as `Replay` rebuilds each later stack
        from the frames before it, and adds those frames to the running mean
        and variance.
        """
        pressed = frombuffer(frames, uint8).reshape(-1, *self.shape[1:])

        self.replay.begin({Entry.FRAMES: start.stack(self.shape)})

        for frame in pressed:
            self.replay.store(0, {Entry.FRAMES: frame[None]}, 0.0, False)

        self.normalizer.update(pressed)

    @inference_mode()
    def score(self, snapshots: Iterable[Snapshot]) -> list[float]:
        """
        Measures the uncertainty of the frame stack each of `snapshots`
        holds, which it evaluates without building an autograd graph.
        """
        return self.error(
            as_tensor(
                array([snapshot.stack(self.shape) for snapshot in snapshots]),
                device = self.device
            )
        ).tolist()

    def train(self, presses: int) -> float | None:
        """
        Takes the updates owed once a search has taken `presses` presses,
        one for every `update_steps` of them.

        Returns:
            The mean loss over the updates it took, or `None` where it took
            none.
        """
        losses = [
            self.update()
            for _ in range(presses // self.settings.update_steps - self.updates)
        ]

        return fmean(losses) if losses else None

    def update(self) -> float:
        """
        Takes one gradient step on the mean squared error between the
        predictor and the target on a batch drawn from replay memory.

        Returns:
            The loss.
        """
        batch = self.replay.sample(self.device, self.settings.batch_size)
        loss  = self.error(batch.next_observations[Entry.FRAMES]).mean()

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        self.updates += 1

        return loss.item()
