"""
Defines `Trainer`, the training loop of one run, which `squirtl train`
drives through each step of the run, as `EpisodeTrainer` plays it for the
deep Q-network and `RolloutTrainer` for PQN and PPO, each continuing a
stopped run from the records `squirtl.runs.handover` declares.
"""

from abc             import abstractmethod
from collections.abc import Iterator, Mapping
from datetime        import datetime
from functools       import cached_property
from gymnasium       import Env, make_vec
from gymnasium.envs.registration import EnvSpec
from gymnasium.vector            import AutoresetMode, VectorEnv
from gymnasium.vector.utils      import concatenate, create_empty_array
from gymnasium.wrappers.vector   import NormalizeReward
from loguru       import logger
from numpy        import flatnonzero, float32, float64, ndarray, uint64, zeros
from numpy.random import Generator, SeedSequence, default_rng
from pathlib      import Path
from typing       import ClassVar

from squirtl.agent.checkpoint      import Checkpoint, ReplayCheckpoint
from squirtl.agent.learner         import DQN, Learner, RolloutAgent
from squirtl.agent.schemas         import Algorithm, Measures, Update
from squirtl.emulator.schemas      import Cartridge
from squirtl.environment.overworld import Overworld
from squirtl.environment.schemas   import Outcome, Recording
from squirtl.environment.workers   import ignore_interrupts
from squirtl.runs.benchmark        import Benchmark
from squirtl.runs.curriculum       import Curriculum
from squirtl.runs.driver           import Driver
from squirtl.runs.handover         import Handover, Moments, Slot, Tally, VectorCheckpoint
from squirtl.runs.schemas          import Episode, Run
from squirtl.runs.settings         import RunSettings, Stream


class Trainer(Driver):
    """
    The training loop of one run, which plays `Overworld` through the agent
    from outside the environment and appends each episode to the run's
    `episodes`. It writes the run's checkpoint where `play` first returns
    at or past each multiple of `checkpoint_steps` and at the run's end,
    evaluates the agent where `play` first returns at or past each multiple
    of `evaluation_steps`, and runs until the run takes its `steps` or is
    stopped where `play` returns.
    """

    checkpoint_class: ClassVar[type[Checkpoint]]
    """
    The checkpoint the trainer writes and a resumed run reads back.
    """

    def __exit__(self, *raised: object):
        """
        Puts back the signal handlers as `Driver` does and closes the
        environment, whether or not the `with` block raised.
        """
        super().__exit__(*raised)
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
                        the agent, as the agent's `restore` raises, or from
                        the demonstration's segments, as the curriculum's
                        `restore` raises, beside each error `Run.start`
                        raises.
        """
        self.cartridge = cartridge
        self.settings  = settings
        self.env       = self.make()
        self.agent     = self.build()

        if handover:
            self.restore(handover.checkpoint)

        self.evaluated = 0
        self.finished  = 0

        super().__init__(
            Run.start(self.digest, settings, started, handover and handover.name)
        )

        if handover:
            self.inherit(handover)

    def __iter__(self) -> Iterator[int]:
        """
        Plays through `play` until the run takes its `steps` or is stopped
        where `play` returns, yielding the agent's step count after each
        step. Before each call to `play` and once the loop ends, it writes
        the checkpoint and plays the evaluation that `due` finds reached,
        which evaluates a run resumed past an evaluation that never landed
        before it plays on. A checkpoint lands where `play` first returns at
        or past each multiple of `checkpoint_steps` and once the loop ends,
        unless the run's own checkpoint already holds the last step, and
        an evaluation where `play` first returns at or past a multiple of
        `evaluation_steps`.
        """
        settings = self.settings

        while True:
            if self.due(settings.checkpoint_steps, self.saved):
                self.checkpoint()

            if self.due(settings.evaluation_steps, self.evaluated):
                self.evaluate()

            if self.agent.step >= settings.steps or self.stopping:
                break

            yield from self.play()

        self.conclude(f"{self.finished:,} episodes")

    @property
    def checkpointed(self) -> Checkpoint:
        """
        Gathers everything a resumed run continues training from, the
        agent's checkpoint unless the trainer adds its own side to it.
        """
        return self.agent.checkpoint

    @cached_property
    def demonstration(self) -> Recording | None:
        """
        Reads the recording of the demonstration the curriculum's settings
        name, as `Run.demonstration` reads it, or `None` where they name
        none.

        Raises:
            FileNotFoundError : Where the directory they name holds no run.
            ValueError        : Where its run ends its episodes at another
                                goal than this run's, or holds no episode
                                reaching its goal from Blue's bedroom.
        """
        if (directory := self.settings.curriculum.demonstration) is None:
            return None

        demonstrated = Run.read(directory)
        theirs, ours = (
            settings.environment.goal
            for settings in (demonstrated.settings, self.settings)
        )

        if theirs is not ours:
            raise ValueError(
                f"the demonstration {directory} ends its episodes at "
                f"{theirs.name}, where this run ends them at {ours.name}"
            )

        return demonstrated.demonstration

    @property
    @abstractmethod
    def digest(self) -> str:
        """
        Reads the digest of the state the environment's intro leaves the
        console in.
        """

    @property
    def logs(self) -> tuple[Path, ...]:
        """
        Lists the run's `episodes`, which a checkpoint follows.
        """
        return (self.run.episodes,)

    @property
    def specification(self) -> EnvSpec:
        """
        Reads the specification of the environment the run plays, along
        `demonstration` where there is one.
        """
        settings = self.settings

        return Overworld.specification(
            self.cartridge,
            settings.emulator,
            settings.environment,
            settings.reward,
            self.demonstration,
            settings.curriculum.tolerance
        )

    @property
    def step(self) -> int:
        """
        Reads the environment steps the agent has taken.
        """
        return self.agent.step

    @abstractmethod
    def build(self) -> Learner:
        """
        Builds the agent the settings name over the environment's spaces,
        seeded from the agent's stream.
        """

    @staticmethod
    @abstractmethod
    def carried(checkpoint: Checkpoint, previous: Run) -> list[str]:
        """
        Reads the line of each episode `previous` wrote before `checkpoint`,
        its last checkpoint, which a resumed run carries over.
        """

    def evaluate(self):
        """
        Evaluates the agent at its step through `Benchmark.from_run`,
        recording the step it landed at, and logs how often the agent and
        the random baseline reached the run's goal and the returns each
        averaged.
        """
        logger.info("Evaluating the agent at step {:,}", self.agent.step)

        benchmark = Benchmark.from_run(self.cartridge, self.run, self.agent.weights)
        self.evaluated = self.agent.step

        logger.info(
            "At step {:,}, the agent reached {} in {:.0%} of its evaluation "
            "episodes for a mean return of {:.4f}, and the random baseline in "
            "{:.0%} for {:.4f}",
            self.evaluated,
            benchmark.agent.goal.name,
            benchmark.agent.reached,
            benchmark.agent.reward,
            benchmark.baseline.reached,
            benchmark.baseline.reward
        )

    def inherit(self, handover: Handover):
        """
        Writes into the run what `handover` carries over, through
        `Handover.write`, counting its episodes among those `finished` and
        the next checkpoint and evaluation on from the steps the last of
        each landed at, so the run goes on as though the run it continues
        had never stopped.
        """
        handover.write(self.run)
        self.evaluated = handover.evaluated
        self.finished  = len(handover.episodes)
        self.saved     = handover.checkpoint.step

        logger.info(
            "Resumed {} at step {:,} after {:,} episodes",
            handover.name,
            self.saved,
            self.finished
        )

    @abstractmethod
    def make(self) -> Env | VectorEnv:
        """
        Makes the environment the settings specify on the cartridge.
        """

    @staticmethod
    def named(algorithm: Algorithm) -> type[Trainer]:
        """
        Reads the class of the training loop of the agent `algorithm` names,
        `EpisodeTrainer` for the deep Q-network and `RolloutTrainer` for PQN
        and PPO.
        """
        return EpisodeTrainer if algorithm is Algorithm.DQN else RolloutTrainer

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

    def restore(self, checkpoint: Checkpoint):
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
        Builds the trainer `named` reads for the agent the settings name,
        raising what its `__init__` raises.
        """
        return Trainer.named(settings.agent.algorithm)(
            cartridge,
            settings,
            started,
            handover
        )


class EpisodeTrainer(Trainer):
    """
    The training loop of the deep Q-network, which plays one episode at a
    time in one environment and may checkpoint, evaluate, or stop at each
    episode's end.
    """

    checkpoint_class = ReplayCheckpoint
    pause            = "episode"

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

    @staticmethod
    def carried(checkpoint: ReplayCheckpoint, previous: Run) -> list[str]:
        """
        Reads the line of each episode `previous` ended by the checkpoint's
        step, which lands at an episode's end, as `Run.ended_by` reads them.
        """
        return previous.ended_by(checkpoint.step)

    def make(self) -> Env:
        """
        Makes one environment through `gymnasium.make`.
        """
        return self.specification.make()

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

    checkpoint_class = VectorCheckpoint
    pause            = "rollout's update"

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
            self.offer()
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
            ],
            syllabus = self.curriculum and self.curriculum.syllabus
        )

    @cached_property
    def curriculum(self) -> Curriculum | None:
        """
        Builds the curriculum along the demonstration from the ends of
        its segments the first environment lists, seeded from the window's
        stream, or `None` where the run follows no demonstration.
        """
        if self.demonstration is None:
            return None

        return Curriculum(
            self.env.unwrapped.get_attr("ends")[0],
            self.settings.seeds[Stream.WINDOW],
            self.settings.curriculum
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
    def carried(checkpoint: VectorCheckpoint, previous: Run) -> list[str]:
        """
        Reads the line of each of the first episodes `previous` wrote, as
        many as the checkpoint's `episodes` counts, as `Run.first` reads
        them.
        """
        return previous.first(checkpoint.episodes)

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
                self.specification,
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

    def offer(self):
        """
        Sets on every environment the starts the curriculum's windows give,
        from which each of its next resets draws, where the run follows
        a demonstration.
        """
        if self.curriculum:
            self.env.unwrapped.set_attr("starts", self.curriculum.starts)

    def play(self) -> Iterator[int]:
        """
        Collects one rollout in every environment, of the `rollout_steps`
        steps the agent's own settings name, from the starts `offer` sets,
        the agent choosing each batch of actions and remembering each batch
        of outcomes, then updates the agent on it. It records each episode
        an environment ends as that step returns, its measures averaged over
        the updates taken while it played, and has the curriculum take in
        each one started along the demonstration.
        """
        self.offer()

        for _ in range(self.settings.agent.hyperparameters.rollout_steps):
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
                final     = info["final_info"]
                outcome   = final["outcome"][slot]
                recording = final["recording"][slot]

                if takeover := recording.takeover:
                    self.curriculum.attempted(
                        length    = outcome.length,
                        succeeded = final["succeeded"][slot].item(),
                        takeover  = takeover
                    )

                self.record(outcome, recording, self.tally.take(slot))

            yield self.agent.step

        self.tally.add(self.agent.update(self.observations))

    def restore(self, checkpoint: VectorCheckpoint):
        """
        Restores the agent from `checkpoint`, then sets each environment's
        generator, plays each unfinished recording back through that
        environment's wrappers at a reset, and sets `NormalizeReward`'s
        statistics and running returns, each environment's tally, and the
        curriculum to what the checkpoint holds, so the run goes on as an
        unbroken one would.
        """
        super().restore(checkpoint)

        if checkpoint.syllabus:
            self.curriculum.restore(checkpoint.syllabus)

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
