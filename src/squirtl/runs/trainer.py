"""
Defines `Trainer`, the training loop of one run, which `squirtl train`
drives through each step of the run.
"""

from collections.abc import Iterator
from contextlib      import AbstractContextManager
from loguru          import logger
from numpy           import uint64
from numpy.random    import SeedSequence
from shutil          import copyfile
from signal          import SIGINT, SIGTERM, signal
from statistics      import fmean
from types           import FrameType
from typing          import Self

from squirtl.agent.learner    import Agent
from squirtl.agent.schemas    import Checkpoint, Update
from squirtl.emulator.schemas import Cartridge
from squirtl.runs.schemas     import Episode, Run, Stream


class Trainer(AbstractContextManager):
    """
    The training loop of one run, which plays each episode of `Overworld`
    through `Agent` from outside the environment and appends each one to the
    run's `episodes`. It writes the agent's checkpoint at the first episode
    end reaching each multiple of `checkpoint_steps` and at the run's end,
    evaluates the agent where an episode end or the run's last step first
    reaches each multiple of `evaluation_steps`, and runs until the run
    takes its `steps` or is stopped at an episode's end.
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

    def __init__(self, cartridge: Cartridge, run: Run):
        """
        Makes the environment from `cartridge` and builds the agent over its
        spaces under the settings `run` records, the agent seeded from its
        own stream, then creates the run's `episodes` empty.
        """
        settings   = run.settings
        self.env   = settings.specification(cartridge).make()
        self.agent = Agent(
            actions  = self.env.action_space.n,
            seed     = settings.seeds[Stream.AGENT],
            settings = settings.agent,
            space    = self.env.observation_space,
            steps    = settings.steps
        )
        self.cartridge   = cartridge
        self.evaluated   = 0
        self.finished    = 0
        self.interrupted = False
        self.run         = run
        self.saved       = 0

        run.episodes.touch()

    def __iter__(self) -> Iterator[int]:
        """
        Plays episodes until the run takes its `steps` or is stopped at an
        episode's end, yielding the agent's step count after each step. It
        writes a checkpoint at the first episode end reaching each multiple
        of `checkpoint_steps` and once the loop ends, unless the run's own
        checkpoint already holds the last step, and evaluates the agent
        where an episode end or the run's last step first reaches a multiple
        of `evaluation_steps`.
        """
        settings = self.run.settings

        while self.agent.step < settings.steps and not self.stopping:
            yield from self.play()

            if self.due(settings.checkpoint_steps, self.saved):
                self.checkpoint()

            if self.due(settings.evaluation_steps, self.evaluated):
                self.evaluate()

        if self.run.stop.exists():
            logger.warning(
                "Stopping at the end of episode {:,} on finding {}",
                self.finished,
                self.run.stop
            )

        if self.saved < self.agent.step or not self.run.checkpoint.exists():
            self.checkpoint()

    @property
    def seed(self) -> int:
        """
        Draws the seed the next episode resets the environment with, from
        the child of the environment stream's `SeedSequence` that the count
        of episodes `finished` names. An episode's start then depends on
        the run's seed and its number alone, so a resumed run draws what an
        unbroken one would.
        """
        return (
            SeedSequence(
                self.run.settings.seeds[Stream.ENVIRONMENT],
                spawn_key = (self.finished,)
            )
            .generate_state(1, uint64)
            .item()
        )

    @property
    def stopping(self) -> bool:
        """
        Reads whether the run stops at the end of its episode, which a
        signal `interrupt` caught or the run's `stop` file sets.
        """
        return self.interrupted or self.run.stop.exists()

    def checkpoint(self):
        """
        Writes the agent's checkpoint, replay memory included, to the run's
        `checkpoint` and records the step it landed at.
        """
        self.agent.checkpoint.save(self.run.checkpoint)
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

        evaluation, baseline = self.run.evaluate(
            self.cartridge,
            self.agent.online.state_dict(),
            self.agent.step
        )
        self.evaluated = self.agent.step

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

    def interrupt(self, number: int, frame: FrameType | None):  # prose: ignore[unsorted-positionals]
        """
        Stops the run at the end of the episode it is playing on the first
        interrupt or termination signal, and raises `KeyboardInterrupt` on
        the next, which ends the run at once on its last checkpoint.

        Raises:
            KeyboardInterrupt: On any signal after the first.
        """
        if self.interrupted:
            logger.warning("Ending at once on the last checkpoint")

            raise KeyboardInterrupt

        self.interrupted = True

        logger.warning(
            "Stopping at the end of the episode, where another interrupt ends the "
            "run at once on its last checkpoint"
        )

    def play(self) -> Iterator[int]:
        """
        Plays one episode, the agent choosing each action, remembering each
        transition, and updating after each step, and yields the agent's
        step count after each one. It records the episode once it terminates
        or truncates, whereas an episode the run's `steps` cut short goes
        unrecorded.
        """
        observation, _ = self.env.reset(seed=self.seed)
        updates        = list[Update]()

        self.agent.begin(observation)

        while self.agent.step < self.run.settings.steps:
            action = self.agent.act(observation)
            observation, reward, terminated, truncated, info = self.env.step(action)
            self.agent.remember(action, observation, reward, terminated)

            if update := self.agent.update():
                updates.append(update)

            logger.debug(
                "Step {:,} took action {} for a reward of {}",
                self.agent.step,
                action,
                reward
            )

            yield self.agent.step

            if terminated or truncated:
                self.record(
                    Episode(
                        **dict(info["outcome"]),
                        epsilon = self.agent.epsilon,
                        loss    = fmean(
                            update.loss for update in updates
                        ) if updates else None,
                        recording = self.env.unwrapped.recording,
                        value     = fmean(
                            update.value for update in updates
                        ) if updates else None
                    )
                )

                return

    def record(self, episode: Episode):
        """
        Appends `episode` to the run's `episodes` as one line, counting it
        among those `finished`, and logs its summary.
        """
        self.write(episode)

        logger.info(
            "Episode {:,} {} after {:,} steps in {:.1f} s: return {:.4f}, "
            "positions {:,}, epsilon {:.3f}, loss {}, value {}",
            self.finished,
            "terminated" if episode.terminated else "truncated",
            episode.length,
            episode.seconds,
            episode.reward,
            episode.positions,
            episode.epsilon,
            *("none" if mean is None else f"{mean:.4g}" for mean in (
                episode.loss, episode.value
            ))
        )

    def resume(self, checkpoint: Checkpoint, previous: Run):
        """
        Restores the agent from `checkpoint`, the last one `previous`
        wrote, counting the next checkpoint on from its step, and copies the
        episodes and the evaluations `previous` recorded up to it into this
        run, dropping any past it, beside the random baseline's evaluation,
        so the run goes on as though `previous` had never stopped.
        """
        self.agent.restore(checkpoint)
        self.saved = checkpoint.step

        for episode in previous.ended_by(checkpoint.step):
            self.write(episode)

        kept = list(previous.evaluated_by(checkpoint.step))
        self.run.append(self.run.evaluations, *kept)
        self.evaluated = kept[-1].step if kept else 0

        if previous.baseline.exists():
            copyfile(previous.baseline, self.run.baseline)

        logger.info(
            "Resumed {} at step {:,} after {:,} episodes",
            previous.directory,
            checkpoint.step,
            self.finished
        )

    def write(self, episode: Episode):
        """
        Appends `episode` to the run's `episodes` as one line of JSON and
        counts it among those `finished`.
        """
        self.run.append(self.run.episodes, episode)
        self.finished += 1
