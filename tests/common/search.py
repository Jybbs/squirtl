"""
Defines what the tests of a search build from:

- `PoolStandIn`, which stands in for `ProcessPoolExecutor`, playing each
  rollout in the process running the test
- `ending`, `particle`, and `snapshot`, which build what a rollout reached, a
  particle, and the environment either stands on, with no emulator behind them
- `boot_in_place`, which boots a worker in the process running the test
- `searched`, which runs a search to its end, and `finish`, which runs a
  searcher to its end, stopping it where `stop_at_thirty` writes its `stop`
  or where `terminate_at_twenty` signals its process group
- `assert_same_checkpoint`, which compares what two searches hold
- `iterations`, which reads each iteration a run records, and `lines`, which
  reads them apart from their wall time
"""

from collections.abc  import Callable, Iterable, Iterator
from compression.zstd import compress
from contextlib       import AbstractContextManager
from datetime         import UTC, datetime
from gymnasium.envs.registration import EnvSpec
from numpy         import full, uint8
from os            import killpg, setsid
from pytest        import MonkeyPatch
from signal        import SIGTERM
from torch.testing import assert_close

from squirtl.emulator.schemas    import Cartridge
from squirtl.environment.schemas import Snapshot
from squirtl.reward.schemas      import Event, Position, ProgressTally
from squirtl.runs.schemas        import Run, RunSettings
from squirtl.runs.searcher       import Searcher
from squirtl.search              import workers
from squirtl.search.checkpoint   import SearchCheckpoint
from squirtl.search.particles    import Search
from squirtl.search.schemas      import Ending, Iteration, Particle
from squirtl.search.workers      import boot


class PoolStandIn(AbstractContextManager):
    """
    Stands in for `ProcessPoolExecutor`, holding the arguments it was built
    with and running its initializer before the first `map`, which plays
    each rollout in the process running the test. It records each shutdown
    beside whether it cancelled the rollouts not yet started.
    """

    def __exit__(self, *raised: object):
        """
        Shuts down as `with` does.
        """
        self.shutdown()

    def __init__(self, **arguments: object):
        """
        Records the arguments `Searcher` builds a pool with.
        """
        self.arguments = arguments
        self.booted    = False
        self.shutdowns = []

    def map[T, R](self, function: Callable[[T], R], items: Iterable[T]) -> Iterator[R]:
        """
        Boots the worker once in the test's process, and calls `function` on
        each of `items`.
        """
        if not self.booted:
            boot_in_place(*self.arguments["initargs"])

            self.booted = True

        return map(function, items)

    def shutdown(self, cancel_futures: bool = False):
        """
        Records the shutdown and closes the environment `boot` made, if any.
        """
        self.shutdowns.append(cancel_futures)

        if self.booted:
            workers.environment.close()


def assert_same_checkpoint(first: SearchCheckpoint, second: SearchCheckpoint):
    """
    Asserts that `first` and `second` hold the same frontier, the same
    arrays bit for bit, the same networks, and the same state of the
    generator drawing each batch.
    """
    assert first.frontier == second.frontier
    assert first.arrays.keys() == second.arrays.keys()
    assert first.networks["sampling"] == second.networks["sampling"]
    assert first.networks["updates"] == second.networks["updates"]

    for name in ("optimizer", "predictor", "target"):
        assert_close(first.networks[name], second.networks[name], atol=0, rtol=0)

    for name, values in first.arrays.items():
        assert values.tobytes() == second.arrays[name].tobytes(), name


def boot_in_place(specification: EnvSpec):
    """
    Runs `boot` on `specification` with the move into a process group of
    its own, the thread ending the worker with its parent, and the close at
    the process's exit left out, since the test's process stays in the group
    the terminal or the runner signals, as the main process of a search
    does, it has no parent `multiprocessing` started, and the test closes
    the environment.
    """
    with MonkeyPatch.context() as patch:
        patch.setattr(workers, "exit_with_parent", lambda: None)
        patch.setattr(workers, "register", lambda _: None)
        patch.setattr(workers, "setpgrp", lambda: None)
        boot(specification)


def drive(search: Search) -> float | None:
    """
    Runs one iteration of `search` to its end.

    Returns:
        The mean loss over the predictor's updates, as `Search.iterate`
        returns it.
    """
    iterating = search.iterate()

    while True:
        try:
            next(iterating)
        except StopIteration as stop:
            return stop.value


def ending(
    dead    : bool            = False,
    events  : Iterable[Event] = (),
    presses : bytes           = b"\x01",
    reward  : float           = 0.0,
    shade   : int             = 0,
    x       : int             = 0
) -> Ending:
    """
    Builds what a rollout of `presses` reached, one frame of `shade` per
    press and the environment `snapshot` builds from `events`, `shade`,
    and `x`.
    """
    return Ending(
        dead     = dead,
        frames   = bytes([shade]) * (72 * 80 * len(presses)),
        presses  = presses,
        reward   = reward,
        snapshot = snapshot(events, shade, x)
    )


def finish(
    searcher : Searcher,
    stop     : Callable[[int, Searcher], None] = lambda *_: None
) -> Run:
    """
    Runs `searcher` to its end, calling `stop` with the presses taken and
    the searcher after each outer step.

    Returns:
        The run it recorded.
    """
    with searcher:
        for presses in searcher:
            stop(presses, searcher)

    return searcher.run


def iterations(run: Run) -> list[Iteration]:
    """
    Reads each iteration `run` recorded.
    """
    return [Iteration.model_validate_json(line) for line in run.lines(run.iterations)]


def lines(run: Run) -> list[Iteration]:
    """
    Reads each iteration `run` recorded, its wall time set to 0.
    """
    return [line.model_copy(update={"seconds": 0.0}) for line in iterations(run)]


def particle(
    node   : int   = 0,
    reward : float = 0.0,
    score  : float = 0.0,
    *,
    events : Iterable[Event] = ()
) -> Particle:
    """
    Builds a particle on `node` holding `reward` and `score`, on the
    environment `snapshot` builds from `events` and `node`.
    """
    return Particle(
        node     = node,
        reward   = reward,
        score    = score,
        snapshot = snapshot(events, x=node)
    )


def searched(search: Search) -> Search:
    """
    Runs iterations of `search` until it finishes.

    Returns:
        The search.
    """
    while not search.finished:
        drive(search)

    return search


def snapshot(events: Iterable[Event] = (), shade: int = 0, x: int = 0) -> Snapshot:
    """
    Builds the environment holding frames of `shade`, with the player on
    square `x` of map 0 and `events` set, and with no state any emulator
    could load.
    """
    position = Position(map=0, x=x, y=0)

    return Snapshot(
        frames    = compress(full((4, 72, 80), shade, uint8).tobytes()),
        state     = b"",
        tally     = ProgressTally.of({}, set(events), {}, position, {position}, 0),
        timer_div = 3
    )


def stop_at_thirty(presses: int, searcher: Searcher):
    """
    Writes the run's `stop` file once `searcher` has taken 30 presses.
    """
    if presses >= 30:
        searcher.run.stop.touch()


def terminate_at_twenty(cartridge: Cartridge, settings: RunSettings):
    """
    Runs a search of `settings` on `cartridge` as the leader of a session
    of its own, sending the termination signal once to its whole process
    group after 20 presses at an outer step some group still plays past, as
    `timeout` signals the group of the command it runs.
    """
    setsid()

    def terminate(presses: int, searcher: Searcher):
        """
        Signals the group once 20 presses have played and a group has outer
        steps left.
        """
        if presses >= 20 and not searcher.interrupted and any(
            group.remaining for group in searcher.search.groups
        ):
            killpg(0, SIGTERM)

    finish(Searcher(cartridge, settings, datetime(2026, 10, 4, tzinfo=UTC)), terminate)
