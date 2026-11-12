"""
Defines `Novelty`, the random network distillation of Burda et al. that
scores how uncertain a search is of a frame stack, as Appendix A.3 of
Mhammedi and Cohan's "Decoupling Exploration and Policy Optimization" sets
it out.
"""

from collections        import defaultdict
from collections.abc    import Iterable, Mapping
from concurrent.futures import Future, ThreadPoolExecutor
from copy               import copy, deepcopy
from gymnasium.spaces   import Box, Dict
from gymnasium.wrappers.utils import RunningMeanStd
from math                import sqrt
from numpy               import array, asarray, concatenate, frombuffer, ndarray, uint8
from numpy.random        import Generator
from statistics          import fmean
from torch               import Tensor, as_tensor, channels_last, default_generator, float32, inference_mode, zeros
from torch.nn            import Identity, LazyLinear, Linear, Module, ReLU, Sequential
from torch.nn.functional import mse_loss
from torch.nn.init       import orthogonal_, zeros_
from torch.optim         import Adam
from torch.random        import fork_rng

from squirtl.agent.networks      import Encoder, configure, weighted
from squirtl.agent.replay        import Replay
from squirtl.agent.schemas       import AgentSettings
from squirtl.environment.schemas import Entry, Snapshot
from squirtl.search.schemas      import SearchSettings


class Novelty:
    """
    A fixed random target network and the predictor trained toward it, whose
    squared error on a frame stack falls the more often replay memory has
    held stacks like it. Each network reads a `(depth, height, width)` stack
    normalized by the running mean and standard deviation of each pixel
    and clipped to `[-5, 5]`. The updates `train` starts run on a thread of
    their own while the search goes on, and until `wait` returns their loss,
    every score reads a copy of the predictor as it stood when they started
    and every frame observed waits outside replay memory.
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
        device and threads `agent` names and with each convolution's weights
        in the `channels_last` memory format, a copy of the predictor that
        scores read while it trains, Adam over the predictor, and empty
        replay memory drawing every batch from `sampling`.

        Args:
            seed: The unsigned 64-bit seed both networks' weights start
                  from.
        """
        configure(agent)

        with fork_rng(devices=[]):
            default_generator.manual_seed(seed)
            self.predictor = self.network(space.shape).to(
                agent.device,
                memory_format = channels_last
            )
            self.target = (
                self.network(space.shape)
                    .to(agent.device, memory_format=channels_last)
                    .requires_grad_(False)
            )

        self.device     = agent.device
        self.executor   = ThreadPoolExecutor(1, "novelty")
        self.normalizer = RunningMeanStd(shape=space.shape[1:])
        self.optimizer  = Adam(self.predictor.parameters(), lr=settings.learning_rate)
        self.pending: list[tuple[ndarray, ndarray]] = []
        self.replay   = Replay(settings.capacity, sampling, Dict({Entry.FRAMES: space}))
        self.scorer   = deepcopy(self.predictor).requires_grad_(False)
        self.settings = settings
        self.shape    = space.shape
        self.training: list[Future[float]] | None = None
        self.updates = 0

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

    def chained(self) -> list[tuple[ndarray, ndarray]]:
        """
        Orders the rollouts waiting outside replay memory into chains,
        each opened by the earliest observed rollout not yet ordered and
        continued by the earliest one not yet ordered that starts from the
        newest stack the last one reached, until none does.

        Returns:
            Each waiting rollout's stack and frames, once each.
        """
        starting = defaultdict(list)

        for index, (stack, _) in enumerate(self.pending):
            starting[stack.tobytes()].append(index)

        order = dict[int, None]()

        for first in range(len(self.pending)):
            index = first

            while index is not None and index not in order:
                order[index] = None
                newest = concatenate(self.pending[index])[-self.shape[0]:].tobytes()
                index  = next(
                    (later for later in starting[newest] if later not in order),
                    None
                )

        return [self.pending[index] for index in order]

    def error(
        self,
        frames     : Tensor,
        normalizer : RunningMeanStd,
        predictor  : Module
    ) -> Tensor:
        """
        Measures the squared error of `predictor` against the target on
        each stack of `frames`, a `(batch, depth, height, width)` tensor
        of `uint8`, after normalizing each pixel by the running statistics
        `normalizer` holds and clipping it, the stacks laid out in the
        `channels_last` memory format the convolutions hold.

        Returns:
            A `(batch,)` tensor.
        """
        mean, deviation = (
            as_tensor(values, device=self.device, dtype=float32)
            for values in (normalizer.mean, normalizer.var ** 0.5)
        )
        inputs = (
            ((frames.to(float32) - mean) / deviation)
            .clamp(-5, 5)
            .contiguous(memory_format=channels_last)
        )

        return mse_loss(
            predictor(inputs),
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

        self.scorer.load_state_dict(networks["predictor"])

        self.normalizer.count = arrays["count"].item()
        self.normalizer.mean  = arrays["mean"]
        self.normalizer.var   = arrays["var"]
        self.optimizer.load_state_dict(networks["optimizer"])
        self.replay.generator.bit_generator.state = networks["sampling"]
        self.updates = networks["updates"]

    @staticmethod
    def network(shape: tuple[int, int, int]) -> Sequential:
        """
        Builds the convolutions `Encoder.encoder` builds for a stack of
        images, unnormalized, beneath the appendix's head, two 1024-unit
        linear layers separated by a ReLU. An observation of zeros sets
        each lazy layer's depth and width, and the convolutions take the
        orthogonal weights and zero biases of Burda et al.'s `conv`, at the
        gain of the square root of 2 their networks pass it.
        """
        network = Sequential(
            Encoder.encoder(Identity, Identity, shape),
            LazyLinear(1024),
            ReLU(),
            Linear(1024, 1024)
        )
        network(zeros(1, *shape))

        for layer in weighted(network[0]):
            orthogonal_(layer.weight, sqrt(2))
            zeros_(layer.bias)

        return network

    def observe(self, frames: bytes, start: Snapshot):
        """
        Adds each newest frame in `frames` to the running mean and variance
        and stores the stack `start` holds, where replay memory does not
        already end on it, and each of those frames after it, as `Replay`
        rebuilds each later stack from the frames before it. While updates
        run, the stack and its frames wait until `wait` stores them, so
        an update draws only from what replay memory held when the updates
        started.
        """
        pressed = frombuffer(frames, uint8).reshape(-1, *self.shape[1:])

        self.normalizer.update(pressed)
        self.pending.append((start.stack(self.shape), pressed))

        if self.training is None:
            self.store()

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
            ),
            self.normalizer,
            self.predictor if self.training is None else self.scorer
        ).tolist()

    def store(self):
        """
        Stores each stack and its frames waiting outside replay memory in
        the order `chained` gives them, storing a stack only where replay
        memory does not already end on it.
        """
        for stack, pressed in self.chained():
            if not self.replay.ends_on({Entry.FRAMES: stack}):
                self.replay.begin({Entry.FRAMES: stack})

            for frame in pressed:
                self.replay.store(0, {Entry.FRAMES: frame[None]}, 0.0, False)

        self.pending.clear()

    def train(self, presses: int):
        """
        Starts the updates owed once a search has taken `presses` presses,
        one for every `update_steps` of them, each a future of its own on
        the executor's one thread, so shutting it down with `cancel_futures`
        cancels every update not yet running, after copying the predictor
        for scores to read meanwhile. Each update normalizes its batch by
        the running statistics as they stand now, so the frames observed
        while the updates run leave them unchanged. A copy of the normalizer
        holds them, since its `update` replaces its arrays rather than
        writing into them.
        """
        self.scorer.load_state_dict(self.predictor.state_dict())
        normalizer    = copy(self.normalizer)
        self.training = [
            self.executor.submit(self.update, normalizer)
            for _ in range(presses // self.settings.update_steps - self.updates)
        ]

    def update(self, normalizer: RunningMeanStd) -> float:
        """
        Takes one gradient step on the mean squared error between the
        predictor and the target on a batch drawn from replay memory,
        normalized by `normalizer`.

        Returns:
            The loss.
        """
        batch = self.replay.sample(self.device, self.settings.batch_size)
        loss  = self.error(
            batch.next_observations[Entry.FRAMES],
            normalizer,
            self.predictor
        ).mean()

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        self.updates += 1

        return loss.item()

    def wait(self) -> float | None:
        """
        Waits for the updates `train` started, if any, raising whatever an
        update raised, then stores each stack and its frames observed while
        they ran.

        Returns:
            The mean loss over the updates, or `None` where none ran.
        """
        training, self.training = self.training, None
        losses = [update.result() for update in training or ()]

        self.store()

        return fmean(losses) if losses else None
