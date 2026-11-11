"""
Defines `Searcher`, the loop of one search over save states, which `squirtl
search` drives through each outer step of the run, beside `SearchHandover`,
what a resumed search takes over from the stopped search it continues.
"""

from collections.abc    import Iterator
from concurrent.futures import ProcessPoolExecutor
from datetime           import datetime
from functools          import partial
from gymnasium          import make
from itertools          import islice
from loguru             import logger
from multiprocessing    import get_context
from pathlib            import Path
from time               import perf_counter
from typing             import Self

from squirtl.emulator.schemas      import Cartridge, Record
from squirtl.environment.overworld import Overworld
from squirtl.environment.schemas   import Entry
from squirtl.runs.driver           import Driver
from squirtl.runs.schemas          import Episode, Run, RunSettings, Stream
from squirtl.search.checkpoint     import SearchCheckpoint
from squirtl.search.particles      import Search
from squirtl.search.schemas        import Iteration
from squirtl.search.workers        import boot, roll


class SearchHandover(Record):
    """
    What a resumed search takes over from the stopped search it continues,
    read whole before the new run writes anything, so a resume refused for
    any of it leaves no directory behind.
    """

    checkpoint: SearchCheckpoint
    """
    The stopped search's last checkpoint, which the search restores.
    """

    iterations: list[str]
    """
    The line of each iteration the checkpoint holds, as the stopped search's
    `iterations` holds it.
    """

    name: str
    """
    The stopped search's name, which the new run records under `resumes`.
    """

    @classmethod
    def from_run(cls, previous: Run) -> Self:
        """
        Reads what `previous` recorded up to its last checkpoint.

        Raises:
            FileNotFoundError : Where `previous` holds no checkpoint.
            ValueError        : Where `previous` is a training run, its
                                checkpoint is damaged or already holds the
                                goal or the run's `steps`, or the iterations
                                `previous` recorded end short of it.
        """
        if not previous.searches:
            raise ValueError(
                f"{previous.directory} holds a training run, which `squirtl train "
                f"--resume` continues"
            )

        checkpoint = SearchCheckpoint.from_path(previous.checkpoint)
        frontier   = checkpoint.frontier

        if (
            previous.settings.environment.goal in frontier.winner.snapshot.tally.events
            or frontier.presses                >= previous.settings.steps
        ):
            raise ValueError(
                f"{previous.checkpoint} already holds the search's end, at press "
                f"{frontier.presses:,}"
            )

        iterations = list(
            islice(previous.lines(previous.iterations), frontier.iterations)
        )

        if len(iterations) < frontier.iterations:
            raise ValueError(
                f"{previous.iterations} ends at iteration {len(iterations):,}, short "
                f"of the checkpoint at iteration {frontier.iterations:,}"
            )

        return cls(checkpoint=checkpoint, iterations=iterations, name=previous.name)


class Searcher(Driver):
    """
    The loop of one search, which runs `Search` over worker processes and
    writes each iteration to the run's `iterations`, and the path to the
    goal, once a particle sets it, to its `episodes` as an episode reaching
    it. It writes a checkpoint at the first iteration end reaching each
    multiple of `checkpoint_steps` and at the search's end, and runs until
    a particle sets the goal, the presses reach the run's `steps`, or it is
    stopped at an iteration's end.
    """

    pause = "iteration"

    def __exit__(self, *raised: object):
        """
        Puts back the signal handlers and shuts the worker processes down,
        dropping each rollout not yet started, whether or not the `with`
        block raised.
        """
        super().__exit__(*raised)
        self.pool.shutdown(cancel_futures=True)

    def __init__(
        self,
        cartridge : Cartridge,
        settings  : RunSettings,
        started   : datetime,
        handover  : SearchHandover | None = None
    ):
        """
        Makes the environment from `cartridge` once, for the snapshot of the
        reset every particle starts from, and builds the search over worker
        processes, each making the environment of its own as it starts.
        The search is restored from the checkpoint `handover` carries where
        there is one, and only then does the run start at `started`, so a
        checkpoint that differs from the search leaves no directory behind.

        Raises:
            ValueError: Where the checkpoint `handover` carries differs from
                        the search, as `Search.restore` raises, beside each
                        error `Run.start` raises.
        """
        self.specification = Overworld.specification(
            cartridge,
            settings.emulator,
            settings.environment,
            settings.reward
        )
        seed = settings.seeds[Stream.SEARCH]

        self.pool = ProcessPoolExecutor(
            initargs    = (self.specification,),
            initializer = boot,
            max_workers = settings.search.workers,
            mp_context  = get_context("spawn")
        )

        with self.specification.make() as env:
            env.reset(seed=seed)

            digest      = env.unwrapped.digest
            self.search = Search(
                actions  = env.action_space.n,
                agent    = settings.agent,
                goal     = settings.environment.goal,
                roll     = partial(self.pool.map, roll),
                root     = env.get_wrapper_attr("capture")(),
                seed     = seed,
                settings = settings.search,
                space    = env.observation_space[Entry.FRAMES],
                steps    = settings.steps
            )

        if handover:
            self.search.restore(handover.checkpoint)

        super().__init__(
            Run.start(
                digest,
                settings,
                started,
                handover and handover.name,
                searches = True
            )
        )

        if handover:
            self.inherit(handover)

    def __iter__(self) -> Iterator[int]:
        """
        Runs iterations until the search finishes or is stopped at an
        iteration's end, yielding the presses taken after each outer step,
        and records the path to the goal once a particle sets it. It writes
        a checkpoint at the first iteration end reaching each multiple of
        `checkpoint_steps` and once the loop ends, unless the run's own
        checkpoint already holds the last press.
        """
        while not self.search.finished and not self.stopping:
            self.clock = perf_counter()
            self.record((yield from self.search.iterate()))

            if self.due(self.run.settings.checkpoint_steps, self.saved):
                self.checkpoint()

        if self.search.reached:
            self.demonstrate()

        self.conclude(f"{self.search.iterations:,} iterations")

    @property
    def checkpointed(self) -> SearchCheckpoint:
        """
        Gathers the search's checkpoint.
        """
        return self.search.checkpoint

    @property
    def logs(self) -> tuple[Path, ...]:
        """
        Lists the run's `iterations` and `episodes`, which a checkpoint
        follows.
        """
        return self.run.iterations, self.run.episodes

    @property
    def step(self) -> int:
        """
        Reads the presses the search's rollouts have taken.
        """
        return self.search.presses

    def demonstrate(self):
        """
        Plays the winner's path from Blue's bedroom through an environment
        whose `TimeLimit` lets it run to its end, and appends the episode
        it plays to the run's `episodes`, so a curriculum takes it as its
        demonstration and `squirtl watch` plays it.
        """
        recording = self.search.demonstration

        with make(
            self.specification,
            max_episode_steps = max(
                len(recording.presses),
                self.run.settings.environment.max_episode_steps
            )
        ) as env:
            env.reset(options={"recording": recording})

            for action in recording.presses:
                *_, info = env.step(action)

        episode = Episode(
            **dict(info["outcome"]),
            epsilon   = None,
            recording = recording,
            update    = None
        )

        self.run.append(self.run.episodes, episode)

        logger.info(
            "Found a path of {:,} presses to {} for a return of {:.4f}",
            episode.length,
            self.run.settings.environment.goal.name,
            episode.reward
        )

    def inherit(self, handover: SearchHandover):
        """
        Writes into the run each iteration `handover` carries over, and
        counts the next checkpoint on from the press the last one landed at,
        so the search goes on as though the search it continues had never
        stopped.
        """
        self.run.iterations.write_text("".join(handover.iterations), encoding="utf-8")
        self.saved = self.step

        logger.info(
            "Resumed {} at press {:,} after {:,} iterations",
            handover.name,
            self.saved,
            self.search.iterations
        )

    def record(self, loss: float | None):
        """
        Appends the iteration just run to the run's `iterations` as one line
        of JSON, the time since `clock` its wall time, and logs its summary.

        Args:
            loss: The mean loss over the predictor's updates, if any.
        """
        winner    = self.search.winner
        tree      = self.search.tree
        iteration = Iteration(
            length    = len(self.search.demonstration.presses),
            loss      = loss,
            memory    = tree.nbytes,
            nodes     = len(tree),
            positions = len(winner.snapshot.tally.reached),
            presses   = self.search.presses,
            reward    = winner.reward,
            seconds   = perf_counter() - self.clock
        )

        self.run.append(self.run.iterations, iteration)

        logger.info(
            "Iteration {:,} reached a reward of {:.4f} and {:,} positions at press "
            "{:,} in {:.1f} s: path {:,} presses, tree {:,} nodes and {:,} bytes, "
            "loss {}",
            self.search.iterations,
            iteration.reward,
            iteration.positions,
            iteration.presses,
            iteration.seconds,
            iteration.length,
            iteration.nodes,
            iteration.memory,
            "none" if loss is None else f"{loss:.4g}"
        )
