"""
Pins the loop of one search, covering:

- The line each iteration writes and the path it leaves, written at each
  iteration's end, and a directory recording itself as a search
- The checkpoint at the first iteration end reaching each interval and at
  the search's end, each written after the iterations are flushed to disk
- A search ending at the starter or at its steps, and a `stop` file, an
  interrupt, or a termination signal ending it at an iteration's end, with a
  second interrupt ending it at once
- A search stopped halfway and resumed ending as one that never stopped, and
  a checkpoint differing from the search refused with no directory left behind
- The pool of worker processes, spawned at the count the settings name, shut
  down whether or not the block raised, and a real one running a search
"""

from collections.abc import Callable
from common.search   import PoolStandIn, assert_same_checkpoint, lines
from pytest          import MonkeyPatch, mark, raises
from signal          import SIGINT, SIGTERM, Signals, getsignal, raise_signal

from squirtl.emulator.schemas    import Cartridge
from squirtl.environment.schemas import Recording
from squirtl.runs.schemas        import Run, Stream
from squirtl.runs.searcher       import Searcher
from squirtl.search.checkpoint   import SearchCheckpoint
from squirtl.search.schemas      import Iteration, SearchSettings
from squirtl.search.workers      import boot


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


def landing(built: Searcher, monkeypatch: MonkeyPatch) -> list[int]:
    """
    Records the press each checkpoint of `built` lands at.

    Returns:
        The list each checkpoint appends to.
    """
    landed  = []
    written = built.checkpoint

    monkeypatch.setattr(
        built,
        "checkpoint",
        lambda: landed.append(built.step) or written()
    )

    return landed


def signaling(number: Signals) -> Callable[[int, Searcher], None]:
    """
    Builds the `stop` raising the signal `number` once 20 presses have
    played, unless a signal has already interrupted the searcher.
    """

    def stop(presses: int, searcher: Searcher):
        """
        Raises the signal.
        """
        if presses >= 20 and not searcher.interrupted:
            raise_signal(number)

    return stop


def stop_at_thirty(presses: int, searcher: Searcher):
    """
    Writes the run's `stop` file once `searcher` has taken 30 presses.
    """
    if presses >= 30:
        searcher.run.stop.touch()


def test_a_checkpoint_follows_the_iterations_it_holds_onto_the_disk(
    monkeypatch : MonkeyPatch,
    searcher    : Callable[..., Searcher]
):
    """
    Asserts that each checkpoint flushes the iterations to disk before the
    archive lands, so none runs ahead of the lines recorded before it.
    """
    calls = []
    sync  = Run.sync
    save  = SearchCheckpoint.save

    monkeypatch.setattr(
        Run,
        "sync",
        lambda run, path: calls.append(path.name) or sync(run, path)
    )
    monkeypatch.setattr(
        SearchCheckpoint,
        "save",
        lambda checkpoint, path: calls.append(path.name) or save(checkpoint, path)
    )
    finish(searcher(checkpoint_steps=20, steps=30))

    assert calls[:2] == ["iterations.jsonl", "checkpoint.npz"]


def test_a_checkpoint_lands_at_the_first_iteration_end_past_each_interval(
    monkeypatch : MonkeyPatch,
    searcher    : Callable[..., Searcher]
):
    """
    Asserts that a search writes a checkpoint at the first iteration end
    reaching each interval of presses and at its end, and that its last
    checkpoint holds the last press.
    """
    built  = searcher(checkpoint_steps=20)
    landed = landing(built, monkeypatch)
    run    = finish(built)

    assert len(landed) >= 2
    assert all(
        last // 20 < step // 20 or step == built.step
        for last, step in zip([0, *landed], landed, strict=False)
    )
    assert landed[-1] == built.step
    assert SearchCheckpoint.from_path(run.checkpoint).frontier.presses == built.step


def test_a_resume_refuses_another_search_and_leaves_no_directory(
    searcher: Callable[..., Searcher]
):
    """
    Asserts that a checkpoint whose networks differ from those the settings
    build raises before the new run makes a directory.
    """
    stopped = finish(searcher(), stop_at_thirty)
    frames  = stopped.settings.environment.model_copy(
        update = {"frame_shape": (36, 40)}
    )

    with raises(ValueError):
        searcher(environment=frames, resumes=stopped)

    assert [*stopped.directory.parent.iterdir()] == [stopped.directory]


def test_a_search_builds_a_pool_of_spawned_workers_booting_its_environment(
    cartridge : Cartridge,
    pools     : list[PoolStandIn],
    searcher  : Callable[..., Searcher]
):
    """
    Asserts that the search asks for the workers its settings name, spawned
    rather than forked, each booted on the run's environment.
    """
    built = searcher()

    arguments = pools[-1].arguments

    assert (arguments["max_workers"], arguments["initializer"]) == (
        built.run.settings.search.workers, boot
    )
    assert arguments["mp_context"].get_start_method() == "spawn"
    assert arguments["initargs"] == (built.run.settings.specification(cartridge),)


def test_a_search_draws_its_root_from_the_seed_of_its_stream(
    searcher: Callable[..., Searcher]
):
    """
    Asserts that the root's `timer_div` is the one the environment's
    generator draws from the seed of the search's own stream, so another run
    seed reaches another.
    """
    built = [searcher(seed=seed) for seed in (1, 2)]

    assert len({each.search.demonstration.timer_div for each in built}) == 2
    assert len({each.run.settings.seeds[Stream.SEARCH] for each in built}) == 2


def test_a_search_ending_at_its_last_checkpoint_writes_no_second_one(
    monkeypatch : MonkeyPatch,
    searcher    : Callable[..., Searcher]
):
    """
    Asserts that a search whose last iteration writes a checkpoint on its
    interval writes no second one holding the same press.
    """
    built  = searcher(checkpoint_steps=1)
    landed = landing(built, monkeypatch)

    finish(built)

    assert len(landed) == len(set(landed))


def test_a_search_ends_at_the_starter_on_a_demonstration_reaching_it(
    searcher: Callable[..., Searcher]
):
    """
    Asserts that a search whose presses reach the starter ends well short of
    its steps, its winner holding the flag.
    """
    built = searcher(steps=100_000)

    finish(built)

    assert built.search.winner.terminated and built.step < 100_000


def test_a_search_records_itself_as_one_with_its_settings(
    searcher: Callable[..., Searcher]
):
    """
    Asserts that a search's directory holds a record marking it as a search,
    beside the settings it read and no run it resumes.
    """
    run  = finish(searcher())
    read = Run.read(run.directory)

    assert (read.searches, read.resumes, read.settings) == (True, None, run.settings)


def test_a_search_shuts_its_pool_down_whether_or_not_it_raised(
    pools    : list[PoolStandIn],
    searcher : Callable[..., Searcher]
):
    """
    Asserts that leaving the block shuts the pool down dropping each rollout
    not yet started, on the way out of a raising block too.
    """
    with raises(KeyboardInterrupt), searcher():
        raise KeyboardInterrupt

    assert pools[-1].shutdowns == [True]


def test_a_search_stopped_halfway_and_resumed_ends_as_one_that_never_stopped(
    searcher: Callable[..., Searcher]
):
    """
    Asserts that a search stopped at an iteration's end and resumed reaches
    the demonstration, tree, networks, and lines of one taken through in
    one go, apart from the wall time each line took, and that it records the
    search it resumes.
    """
    unbroken = finish(searcher())
    stopped  = finish(searcher(), stop_at_thirty)
    resumed  = finish(searcher(resumes=stopped))

    assert lines(unbroken) == lines(resumed)
    assert unbroken.demonstration.read_text("utf-8") == resumed.demonstration.read_text(
        "utf-8"
    )
    assert resumed.resumes == stopped.name
    assert_same_checkpoint(
        SearchCheckpoint.from_path(unbroken.checkpoint),
        SearchCheckpoint.from_path(resumed.checkpoint)
    )


def test_a_second_interrupt_ends_the_search_at_once_on_its_last_checkpoint(
    searcher: Callable[..., Searcher]
):
    """
    Asserts that a second interrupt raises `KeyboardInterrupt` straight
    away, and that the handlers each signal had come back.
    """
    built   = searcher()
    handler = getsignal(SIGINT)

    def twice(presses: int, *_: Searcher):
        """
        Raises the signal twice over once 20 presses have played, under a
        handler other than the one the test began with.
        """
        if presses >= 20:
            assert getsignal(SIGINT) != handler

            raise_signal(SIGINT)
            raise_signal(SIGINT)

    with raises(KeyboardInterrupt):
        finish(built, twice)

    assert getsignal(SIGINT) == handler


def test_a_stop_file_ends_the_search_at_its_iterations_end(
    logged   : list[str],
    searcher : Callable[..., Searcher]
):
    """
    Asserts that a `stop` file found mid-iteration lets that iteration end,
    writes a checkpoint holding its presses, and logs the stop.
    """
    built = searcher()
    run   = finish(built, stop_at_thirty)
    line  = iterations(run)[-1]

    assert built.step < built.run.settings.steps
    assert SearchCheckpoint.from_path(run.checkpoint).frontier.presses == line.presses
    assert any(
        f"Stopping at the end of iteration {built.search.iterations}" in message
        for message in logged
    )


def test_a_termination_signal_stops_the_search_as_an_interrupt_does(
    searcher: Callable[..., Searcher]
):
    """
    Asserts that a termination signal stops the search at its iteration's
    end.
    """
    built = searcher()

    finish(built, signaling(SIGTERM))

    assert built.interrupted and built.step < built.run.settings.steps


def test_an_interrupt_ends_the_search_at_its_iterations_end(
    logged   : list[str],
    searcher : Callable[..., Searcher]
):
    """
    Asserts that a first interrupt lets the iteration end, naming that unit
    in what it logs, and that the search's checkpoint holds that iteration.
    """
    built = searcher()
    run   = finish(built, signaling(SIGINT))

    assert any("end of the iteration" in message for message in logged)
    assert built.step < built.run.settings.steps
    assert SearchCheckpoint.from_path(run.checkpoint).frontier.presses == built.step


def test_an_iteration_with_no_update_owed_records_no_loss(
    searcher: Callable[..., Searcher]
):
    """
    Asserts that a line holds no loss where its iteration owed no update of
    the predictor, whereas one owing an update holds a loss.
    """
    settings = SearchSettings(
        batch_size   = 4,
        capacity     = 64,
        groups       = 2,
        inner_steps  = (2, 2),
        outer_steps  = (1, 1),
        particles    = 2,
        update_steps = 12,
        workers      = 1
    )
    lines = iterations(finish(searcher(search=settings, steps=24)))

    assert [line.loss is None for line in lines] == [True, False, False]


def test_each_iteration_writes_a_line_and_the_path_it_leaves(
    searcher: Callable[..., Searcher]
):
    """
    Asserts that every iteration writes one line counting its presses, tree,
    path, wall time, and memory, and that the demonstration on disk holds as
    many presses as the last line's length and earns its reward.
    """
    built = searcher()
    run   = finish(built)
    lines = iterations(run)

    demonstration = Recording.model_validate_json(run.demonstration.read_text("utf-8"))

    assert len(lines) == built.search.iterations > 1
    assert [line.presses for line in lines] == sorted(line.presses for line in lines)
    assert all(
        line.seconds > 0.0 and line.memory > 0 and line.nodes > 0 for line in lines
    )
    assert (
        lines[-1].presses,
        lines[-1].reward
    ) == (built.step, built.search.winner.reward)
    assert (lines[-1].length, demonstration) == (
        len(demonstration.presses),
        built.search.demonstration
    )
    assert not run.demonstration.with_name("demonstration.json.partial").exists()


@mark.usefixtures("clone", "rom")
def test_a_search_over_a_real_pool_reaches_the_lines_of_one_in_the_process(
    actual   : Callable[..., Searcher],
    searcher : Callable[..., Searcher]
):
    """
    Asserts that a real pool of two spawned workers records the same lines
    as a search on one worker in this process, which the workers' order
    cannot change, on a cartridge whose presses each process plays alike.
    """
    settings = {"checkpoint_steps": 40, "steps": 40}
    real     = finish(actual(**settings))
    twin     = finish(
        searcher = actual(
            **settings,
            search = real.settings.search.model_copy(update={"workers": 1})
        )
    )

    assert lines(real) == lines(twin)
    assert real.demonstration.read_text("utf-8") == twin.demonstration.read_text(
        "utf-8"
    )
