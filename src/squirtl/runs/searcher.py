"""
Defines `Searcher`, the loop of one search over save states, which `squirtl
search` drives through each outer step of the run.
"""

from collections.abc    import Iterator
from concurrent.futures import ProcessPoolExecutor
from datetime           import datetime
from functools          import partial
from loguru             import logger
from multiprocessing    import get_context
from time               import perf_counter

from squirtl.emulator.schemas    import Cartridge
from squirtl.environment.schemas import Entry
from squirtl.runs.driver         import Driver
from squirtl.runs.schemas        import Run, RunSettings, SearchHandover, Stream
from squirtl.search.checkpoint   import SearchCheckpoint
from squirtl.search.particles    import Search
from squirtl.search.schemas      import Iteration
from squirtl.search.workers      import boot, roll


class Searcher(Driver):
    """
    The loop of one search, which runs `Search` over worker processes and
    writes each iteration to the run's `iterations` and the winner's path to
    its `demonstration`. It writes a checkpoint at the first iteration end
    reaching each multiple of `checkpoint_steps` and at the search's end,
    and runs until a particle sets `EVENT_GOT_STARTER`, the presses reach
    the run's `steps`, or it is stopped at an iteration's end.
    """

    handover = SearchHandover
    unit     = "iteration"

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
        Makes the environment from `cartridge` once, for the snapshot of
        the reset every particle starts from, and builds the search over
        worker processes, each making the environment of its own at its
        first rollout. The search is restored from the checkpoint `handover`
        carries where there is one, and only then does the run start at
        `started`, so a checkpoint that differs from the search leaves no
        directory behind.

        Raises:
            ValueError: Where the checkpoint `handover` carries differs from
                        the search, as `Search.restore` raises, beside each
                        error `Run.start` raises.
        """
        specification = settings.specification(cartridge)
        seed          = settings.seeds[Stream.SEARCH]

        self.pool = ProcessPoolExecutor(
            initargs    = (specification,),
            initializer = boot,
            max_workers = settings.search.workers,
            mp_context  = get_context("spawn")
        )

        with specification.make() as env:
            env.reset(seed=seed)

            digest      = env.unwrapped.digest
            self.search = Search(
                actions  = env.action_space.n,
                agent    = settings.agent,
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
        iteration's end, yielding the presses taken after each outer step.
        It writes a checkpoint at the first iteration end reaching each
        multiple of `checkpoint_steps` and once the loop ends, unless the
        run's own checkpoint already holds the last press.
        """
        while not self.search.finished and not self.stopping:
            self.clock = perf_counter()
            self.record((yield from self.search.iterate()))

            if self.due(self.run.settings.checkpoint_steps, self.saved):
                self.checkpoint()

        self.conclude(self.search.iterations)

    @property
    def state(self) -> SearchCheckpoint:
        """
        Gathers the search's checkpoint.
        """
        return self.search.checkpoint

    @property
    def step(self) -> int:
        """
        Reads the presses the search's rollouts have taken.
        """
        return self.search.presses

    def inherit(self, handover: SearchHandover):
        """
        Writes into the run each iteration `handover` carries over and the
        winner's path, and counts the next checkpoint on from the press the
        last one landed at, so the search goes on as though the search it
        continues had never stopped.
        """
        self.run.iterations.write_text("".join(handover.iterations), encoding="utf-8")
        self.run.demonstrate(self.search.demonstration)
        self.saved = self.step

        logger.info(
            "Resumed {} at press {:,} after {:,} iterations",
            handover.name,
            self.saved,
            self.search.iterations
        )

    def record(self, loss: float | None):
        """
        Writes the winner's path to the run's `demonstration`, then appends
        the iteration just run to its `iterations` as one line of JSON, the
        time since `clock` its wall time, and logs its summary.

        Args:
            loss: The mean loss over the predictor's updates, if any.
        """
        demonstration = self.search.demonstration
        winner        = self.search.winner
        tree          = self.search.tree
        iteration     = Iteration(
            length    = len(demonstration.presses),
            loss      = loss,
            memory    = tree.nbytes,
            nodes     = len(tree),
            positions = len(winner.snapshot.tally.reached),
            presses   = self.search.presses,
            reward    = winner.reward,
            seconds   = perf_counter() - self.clock
        )

        self.run.demonstrate(demonstration)
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
