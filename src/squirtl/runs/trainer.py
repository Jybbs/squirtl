"""
Defines `Trainer`, the training loop of one run, which `squirtl train`
drives through each step of the run, as `EpisodeTrainer` plays it for the
deep Q-network and `RolloutTrainer` for PQN and PPO, beside `Tally`, the
sums of the measures each environment's episode averages.
"""

from abc              import ABC, abstractmethod
from collections.abc  import Iterator, Mapping
from contextlib       import AbstractContextManager
from datetime         import datetime
from gymnasium        import Env, make_vec
from gymnasium.vector import AutoresetMode, VectorEnv
from gymnasium.vector.utils    import concatenate, create_empty_array
from gymnasium.wrappers.vector import NormalizeReward
from loguru       import logger
from numpy        import flatnonzero, float32, float64, int64, ndarray, uint64, zeros
from numpy.random import Generator, SeedSequence, default_rng
from signal       import SIGINT, SIGTERM, signal
from types        import FrameType
from typing       import ClassVar, Self

from squirtl.agent.learner       import DQN, RolloutAgent
from squirtl.agent.schemas       import Measures, ReplayCheckpoint, Update
from squirtl.emulator.schemas    import Cartridge
from squirtl.environment.schemas import Outcome, Recording
from squirtl.environment.workers import ignore_interrupts
from squirtl.runs.schemas        import Episode, Handover, Moments, Run, RunSettings, Slot, Stream, VectorCheckpoint


class Tally:
    """
    The sums of the measures of the updates taken while each environment's
    episode played, beside the count of those updates, which an episode's
    record averages once it ends.
    """

    def __init__(self, environments: int, measures: type[Measures]):
        """
        Starts every environment's sums at 0 for the fields of `measures`.
        """
        self.counts   = zeros(environments, int64)
        self.measures = measures
        self.totals   = zeros((environments, len(measures.model_fields)))

    def add(self, update: Measures):
        """
        Adds the measures of `update` to every environment's sums.
        """
        self.counts += 1
        self.totals += update.totals

    def take(self, slot: int) -> Measures | None:
        """
        Averages the sums of the environment at `slot` and starts them again
        at 0, as its episode ends.

        Returns:
            Each measure averaged over the updates taken while the episode
            played, or `None` where none was.
        """
        count, totals     = self.counts[slot].item(), self.totals[slot].tolist()
        self.counts[slot] = 0
        self.totals[slot] = 0

        return self.measures.averaged(count, totals) if count else None


class Trainer(AbstractContextManager, ABC):
    """
    The training loop of one run, which plays `Overworld` through the agent
    from outside the environment and appends each episode to the run's
    `episodes`. It writes the run's checkpoint where `play` first returns
    at or past each multiple of `checkpoint_steps` and at the run's end,
    evaluates the agent where `play` first returns at or past each multiple
    of `evaluation_steps`, and runs until the run takes its `steps` or is
    stopped where `play` returns.
    """

    pause: ClassVar[str]
    """
    Where a stopped run ends, naming the point at which `play` returns.
    """

    def __enter__(self) -> Self:
        """
        Takes over the interrupt and termination signals for `interrupt`,
        keeping the handlers they had for `__exit__` to put back.
        """
        self.handlers = {
            number: signal(number, self.interrupt) for number in (SIGINT, SIGTERM)
        }

        return self

    def __exit__(self, *raised: object):
        """
        Puts back the handlers each signal had before `__enter__` and closes
        the environment, whether or not the `with` block raised.
        """
        for number, handler in self.handlers.items():
            signal(number, handler)

        self.env.close()

    def __init__(
        self,
        cartridge : Cartridge,
        settings  : RunSettings,
        started   : datetime,
        handover  : Handover | None = None
    ):
        """
        Makes the environment from `cartridge` and builds the agent over its
        spaces under `settings`, the agent seeded from its own stream and
        restored from the checkpoint `handover` carries where there is one.
        Only then does it start the run at `started`, recording the digest
        of the state the environment starts from, and write into it what
        `handover` carries over, so a checkpoint that differs from the agent
        leaves no directory behind.

        Raises:
            ValueError: Where the checkpoint `handover` carries differs from
                        the agent, as the agent's `restore` raises, beside
                        each error `Run.start` raises.
        """
        self.cartridge = cartridge
        self.settings  = settings
        self.env       = self.make()
        self.agent     = self.build()

        if handover:
            self.restore(handover.checkpoint)

        self.evaluated   = 0
        self.finished    = 0
        self.interrupted = False
        self.run         = Run.start(
            self.digest,
            settings,
            started,
            handover and handover.name
        )
        self.saved = 0

        if handover:
            self.inherit(handover)

    def __iter__(self) -> Iterator[int]:
        """
        Plays through `play` until the run takes its `steps` or is stopped
        where `play` returns, yielding the agent's step count after each
        step. It writes a checkpoint where `play` first returns at or past
        each multiple of `checkpoint_steps` and once the loop ends, unless
        the run's own checkpoint already holds the last step, and evaluates
        the agent where `play` first returns at or past a multiple of
        `evaluation_steps`.
        """
        settings = self.settings

        while self.agent.step < settings.steps and not self.stopping:
            yield from self.play()

            if self.due(settings.checkpoint_steps, self.saved):
                self.checkpoint()

            if self.due(settings.evaluation_steps, self.evaluated):
                self.evaluate()

        if self.run.stop.exists():
            logger.warning(
                "Stopping at step {:,} after {:,} episodes on finding {}",
                self.agent.step,
                self.finished,
                self.run.stop
            )

        if self.saved < self.agent.step or not self.run.checkpoint.exists():
            self.checkpoint()

    @property
    @abstractmethod
    def checkpointed(self) -> ReplayCheckpoint | VectorCheckpoint:
        """
        Gathers everything a resumed run continues training from.
        """

    @property
    @abstractmethod
    def digest(self) -> str:
        """
        Reads the digest of the state the environment's intro leaves the
        console in.
        """

    @property
    def stopping(self) -> bool:
        """
        Reads whether the run stops where `play` next returns, which a
        signal `interrupt` caught or the run's `stop` file sets.
        """
        return self.interrupted or self.run.stop.exists()

    @abstractmethod
    def build(self) -> DQN | RolloutAgent:
        """
        Builds the agent the settings name over the environment's spaces,
        seeded from the agent's stream.
        """

    def checkpoint(self):
        """
        Writes the run's `episodes` through to disk, then the checkpoint
        to the run's `checkpoint`, and records the step it landed at, so no
        checkpoint runs ahead of the episodes recorded before it.
        """
        self.run.sync(self.run.episodes)
        self.checkpointed.save(self.run.checkpoint)
        self.saved = self.agent.step

        logger.info("Wrote the checkpoint at step {:,}", self.saved)

    def due(self, interval: int, last: int) -> bool:
        """
        Reads whether the agent's step has reached the first multiple of
        `interval` after `last`, the step a checkpoint or an evaluation
        last landed at, the one a resumed run continues from included, or 0
        before the first.
        """
        return self.agent.step >= (last // interval + 1) * interval

    def evaluate(self):
        """
        Evaluates the agent at its step through `Run.evaluate`, recording
        the step it landed at, and logs how often the agent and the random
        baseline reached the starter and the returns each averaged.
        """
        logger.info("Evaluating the agent at step {:,}", self.agent.step)

        evaluation, baseline = self.run.evaluate(self.cartridge, self.agent.weights)
        self.evaluated       = self.agent.step

        logger.info(
            "At step {:,}, the agent reached the starter in {:.0%} of its "
            "evaluation episodes for a mean return of {:.4f}, and the random "
            "baseline in {:.0%} for {:.4f}",
            self.evaluated,
            evaluation.reached,
            evaluation.reward,
            baseline.reached,
            baseline.reward
        )

    def inherit(self, handover: Handover):
        """
        Writes into the run what `handover` carries over, through
        `Run.inherit`, counting its episodes among those `finished` and the
        next checkpoint and evaluation on from the steps the last of each
        landed at, so the run goes on as though the run it continues had
        never stopped.
        """
        self.run.inherit(handover)
        self.evaluated = handover.evaluated
        self.finished  = len(handover.episodes)
        self.saved     = handover.checkpoint.step

        logger.info(
            "Resumed {} at step {:,} after {:,} episodes",
            handover.name,
            self.saved,
            self.finished
        )

    def interrupt(self, number: int, frame: FrameType | None):  # prose: ignore[unsorted-positionals]
        """
        Stops the run where `play` next returns on the first interrupt or
        termination signal, and raises `KeyboardInterrupt` on the next,
        which ends the run at once on its last checkpoint.

        Raises:
            KeyboardInterrupt: On any signal after the first.
        """
        if self.interrupted:
            logger.warning("Ending at once on the last checkpoint")

            raise KeyboardInterrupt

        self.interrupted = True

        logger.warning(
            "Stopping at the end of the {}, where another interrupt ends the run at "
            "once on its last checkpoint",
            self.pause
        )

    @abstractmethod
    def make(self) -> Env | VectorEnv:
        """
        Makes the environment the settings specify on the cartridge.
        """

    @abstractmethod
    def play(self) -> Iterator[int]:
        """
        Plays until the next point at which the run may checkpoint,
        evaluate, or stop, yielding the agent's step count after each step.
        """

    def record(self, outcome: Outcome, recording: Recording, update: Measures | None):
        """
        Appends the episode to the run's `episodes` as one line, from what
        it reached, the agent's chance of a random action at its last step,
        its `recording`, and the averaged measures of each `update` taken
        while it played, counting it among those `finished`, and logs its
        summary.
        """
        episode = Episode(
            **dict(outcome),
            epsilon   = self.agent.epsilon,
            recording = recording,
            update    = update
        )

        self.run.append(self.run.episodes, episode)
        self.finished += 1

        logger.info(
            "Episode {:,} {} after {:,} steps in {:.1f} s: return {:.4f}, "
            "positions {:,}, epsilon {}, {}",
            self.finished,
            "terminated" if episode.terminated else "truncated",
            episode.length,
            episode.seconds,
            episode.reward,
            episode.positions,
            "none" if episode.epsilon is None else f"{episode.epsilon:.3f}",
            episode.update or "no update"
        )

    def reset_seed(self, key: int) -> int:
        """
        Draws the seed of a reset from the child of the environment stream's
        `SeedSequence` that `key` names.
        """
        return (
            SeedSequence(self.settings.seeds[Stream.ENVIRONMENT], spawn_key=(key,))
            .generate_state(1, uint64)
            .item()
        )

    def restore(self, checkpoint: ReplayCheckpoint | VectorCheckpoint):
        """
        Restores the agent from `checkpoint`.
        """
        self.agent.restore(checkpoint)

    @staticmethod
    def start(
        cartridge : Cartridge,
        settings  : RunSettings,
        started   : datetime,
        handover  : Handover | None = None
    ) -> Trainer:
        """
        Builds the trainer of the agent the settings name, an
        `EpisodeTrainer` for the deep Q-network and a `RolloutTrainer` for
        PQN and PPO, raising what its `__init__` raises.
        """
        trainer = RolloutTrainer if settings.agent.hyperparameters else EpisodeTrainer

        return trainer(cartridge, settings, started, handover)


class EpisodeTrainer(Trainer):
    """
    The training loop of the deep Q-network, which plays one episode at a
    time in one environment and may checkpoint, evaluate, or stop at each
    episode's end.
    """

    pause = "episode"

    @property
    def checkpointed(self) -> ReplayCheckpoint:
        """
        Gathers the agent's checkpoint, replay memory included.
        """
        return self.agent.checkpoint

    @property
    def digest(self) -> str:
        """
        Reads the environment's `digest`.
        """
        return self.env.unwrapped.digest

    @property
    def seed(self) -> int:
        """
        Draws the seed the next episode resets the environment with, under
        the count of episodes `finished`. An episode's start then depends on
        the run's seed and its number alone, so a resumed run draws what an
        unbroken one would.
        """
        return self.reset_seed(self.finished)

    def build(self) -> DQN:
        """
        Builds the deep Q-network over the environment's spaces.
        """
        return DQN(
            actions  = self.env.action_space.n,
            seed     = self.settings.seeds[Stream.AGENT],
            settings = self.settings.agent,
            space    = self.env.observation_space,
            steps    = self.settings.steps
        )

    def make(self) -> Env:
        """
        Makes one environment through `gymnasium.make`.
        """
        return self.settings.specification(self.cartridge).make()

    def play(self) -> Iterator[int]:
        """
        Plays one episode, the agent choosing each action, remembering each
        transition, and updating on the steps its schedule names, and yields
        the agent's step count after each one. It records the episode once
        it terminates or truncates, whereas an episode the run's `steps` cut
        short goes unrecorded.
        """
        observation, _ = self.env.reset(seed=self.seed)
        tally          = Tally(1, Update)

        self.agent.begin(observation)

        while self.agent.step < self.settings.steps:
            action = self.agent.act(observation)
            observation, reward, terminated, truncated, info = self.env.step(action)
            self.agent.remember(action, observation, reward, terminated)

            if update := self.agent.update():
                tally.add(update)

            logger.debug(
                "Step {:,} took action {} for a reward of {}",
                self.agent.step,
                action,
                reward
            )

            yield self.agent.step

            if terminated or truncated:
                self.record(info["outcome"], info["recording"], tally.take(0))

                return


class RolloutTrainer(Trainer):
    """
    The training loop of PQN and PPO, which steps `environments` copies of
    the environment at once through `AsyncVectorEnv` under its `SAME_STEP`
    autoreset mode, each reward passing through `NormalizeReward` at
    the run's discount, and may checkpoint, evaluate, or stop once each
    rollout's update ends. Every episode an environment ends reaches the
    trainer in the info of its last step, which the environment's automatic
    reset follows within that step.
    """

    pause = "rollout's update"

    def __exit__(self, *raised: object):
        """
        Terminates the workers where the `with` block raised, then ends as
        `Trainer` does. `AsyncVectorEnv.close` otherwise calls `step_wait`
        again to finish a pending step, and an interrupt raised inside
        `step_wait` leaves some of the workers' pipes already read, so that
        call blocks forever on a pipe no worker writes to again.
        """
        if any(raised):
            self.env.close(terminate=True)

        super().__exit__(*raised)

    def __init__(
        self,
        cartridge : Cartridge,
        settings  : RunSettings,
        started   : datetime,
        handover  : Handover | None = None
    ):
        """
        Starts the run as `Trainer` does, then resets each environment
        from the seed `seeds` draws for it, unless a checkpoint `handover`
        carries has already set each one back to its unfinished episode.
        """
        self.tally = Tally(
            settings.agent.environments,
            settings.agent.algorithm.measures
        )

        super().__init__(cartridge, settings, started, handover)

        if handover is None:
            self.observations, _ = self.env.reset(seed=self.seeds)

    @property
    def checkpointed(self) -> VectorCheckpoint:
        """
        Gathers the agent's checkpoint beside each environment's
        generator, unfinished recording, and running return, the statistics
        `NormalizeReward` scales each reward by, each environment's tally,
        and the count of episodes the run has written.
        """
        vector = self.env.unwrapped

        return VectorCheckpoint(
            **dict(self.agent.checkpoint),
            episodes = self.finished,
            moments = Moments.model_validate(self.env.return_rms, from_attributes=True),
            slots   = [
                Slot(
                    count     = count,
                    generator = generator.bit_generator.state,
                    recording = recording,
                    returned  = returned,
                    totals    = totals
                )
                for count, generator, recording, returned, totals in zip(
                    self.tally.counts.tolist(),
                    vector.get_attr("np_random"),
                    vector.get_attr("recording"),
                    self.env.accumulated_reward.tolist(),
                    self.tally.totals.tolist(),
                    strict = True
                )
            ]
        )

    @property
    def digest(self) -> str:
        """
        Reads the first environment's `digest`, which every environment
        shares.
        """
        return self.env.unwrapped.get_attr("digest")[0]

    @property
    def seeds(self) -> list[int]:
        """
        Draws the seed each environment's first reset takes, under its
        position, after which each reset draws its `timer_div` from that
        environment's own generator.
        """
        return [self.reset_seed(slot) for slot in range(
            self.settings.agent.environments
        )]

    def bootstraps(self, finals: ndarray | None, truncated: ndarray) -> ndarray:
        """
        Values the final observation of each episode the step truncated,
        which `finals` holds at each environment that ended one and which is
        `None` where none did, as Pardo et al. bootstrap at a time limit.

        Returns:
            One value per environment, 0 where the step truncated no episode.
        """
        bootstraps = zeros(len(truncated), float32)

        if truncated.any():
            space             = self.env.single_observation_space
            slots             = flatnonzero(truncated)
            bootstraps[slots] = self.agent.value(
                concatenate(space, finals[slots], create_empty_array(space, len(slots)))
            )

        return bootstraps

    def build(self) -> RolloutAgent:
        """
        Builds PQN or PPO over the environments' spaces.
        """
        return RolloutAgent.named(self.settings.agent.algorithm)(
            actions      = self.env.single_action_space.n,
            environments = self.settings.agent.environments,
            seed         = self.settings.seeds[Stream.AGENT],
            settings     = self.settings.agent,
            space        = self.env.single_observation_space,
            steps        = self.settings.steps
        )

    @staticmethod
    def generator(state: Mapping[str, object]) -> Generator:
        """
        Builds a generator holding `state`.
        """
        generator = default_rng()
        generator.bit_generator.state = state

        return generator

    def make(self) -> NormalizeReward:
        """
        Makes the environments through `gymnasium.make_vec`, each
        in a worker process that ignores the interrupt signal, at
        most `max_concurrency` stepping at once, and wraps them in
        `NormalizeReward`.
        """
        agent = self.settings.agent

        return NormalizeReward(
            make_vec(
                self.settings.specification(self.cartridge),
                num_envs      = agent.environments,
                vector_kwargs = {
                    "autoreset_mode"  : AutoresetMode.SAME_STEP,
                    "max_concurrency" : agent.max_concurrency,
                    "worker"          : ignore_interrupts
                },
                vectorization_mode = "async"
            ),
            gamma = agent.discount
        )

    def play(self) -> Iterator[int]:
        """
        Collects one rollout of `rollout_steps` steps in every environment,
        the agent choosing each batch of actions and remembering each batch
        of outcomes, then updates the agent on it. It records each episode
        an environment ends as that step returns, its measures averaged over
        the updates taken while it played.
        """
        for _ in range(self.settings.agent.rollout_steps):
            self.observations, rewards, terminated, truncated, info = self.env.step(
                self.agent.act(self.observations)
            )

            self.agent.remember(
                self.bootstraps(info.get("final_obs"), truncated),
                rewards,
                terminated,
                truncated
            )

            for slot in flatnonzero(terminated | truncated):
                self.record(
                    info["final_info"]["outcome"][slot],
                    info["final_info"]["recording"][slot],
                    self.tally.take(slot)
                )

            yield self.agent.step

        self.tally.add(self.agent.update(self.observations))

    def restore(self, checkpoint: VectorCheckpoint):
        """
        Restores the agent from `checkpoint`, then sets each environment's
        generator, plays each unfinished recording back through that
        environment's wrappers at a reset, and sets `NormalizeReward`'s
        statistics and running returns and each environment's tally to what
        the checkpoint holds, so the run goes on as an unbroken one would.
        """
        super().restore(checkpoint)

        vector = self.env.unwrapped
        vector.set_attr(
            "np_random",
            [self.generator(slot.generator) for slot in checkpoint.slots]
        )
        vector.set_attr("resumed", [slot.recording for slot in checkpoint.slots])

        self.observations, _ = self.env.reset()

        self.env.accumulated_reward[:] = [slot.returned for slot in checkpoint.slots]
        self.env.return_rms.count      = checkpoint.moments.count

        # A bare `float` gives way to a batch's `float32` under NumPy's promotion rules.
        self.env.return_rms.mean = float64(checkpoint.moments.mean)
        self.env.return_rms.var  = float64(checkpoint.moments.var)

        self.tally.counts[:] = [slot.count for slot in checkpoint.slots]
        self.tally.totals[:] = [slot.totals for slot in checkpoint.slots]
