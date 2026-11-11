"""
Pins the loop of one search, covering:

- The line each iteration writes and the path it leaves, written at each
  iteration's end, and a directory recording itself as a search
- The checkpoint at the first iteration end reaching each interval and at
  the search's end, each written after the iterations are flushed to disk
- A search ending at its goal, writing the path as an episode, or at its
  steps, and a `stop` file, an
  interrupt, or a termination signal ending it at an iteration's end, with a
  second interrupt ending it at once
- A search stopped halfway and resumed ending as one that never stopped, and
  a checkpoint differing from the search refused with no directory left behind
- The handover a resume reads, and the training run, the search at its
  steps or its goal, the missing checkpoint, and the short iterations it
  refuses
- The pool of worker processes, spawned at the count the settings name, shut
  down whether or not the block raised, and a real one running a search
"""

from collections.abc import Callable
from common.search   import PoolStandIn, assert_same_checkpoint, finish, iterations, lines, stop_at_thirty
from itertools       import pairwise
from pytest          import MonkeyPatch, mark, raises
from signal          import SIGINT, SIGTERM, Signals, getsignal, raise_signal

from squirtl.runs.schemas      import Run, Stream
from squirtl.runs.searcher     import SearchHandover, Searcher
from squirtl.search.checkpoint import SearchCheckpoint
from squirtl.search.schemas    import Iteration, SearchSettings
from squirtl.search.workers    import boot


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


def test_a_checkpoint_follows_the_iterations_it_holds_onto_the_disk(
    monkeypatch : MonkeyPatch,
    searcher    : Callable[..., Searcher]
):
    """
    Asserts that each checkpoint flushes the iterations and the episodes to
    disk before the archive lands, so none runs ahead of the lines recorded
    before it.
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

    assert calls[:3] == ["iterations.jsonl", "episodes.jsonl", "checkpoint.npz"]


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


def test_a_handover_reads_the_lines_its_checkpoint_holds(halted: Run):
    """
    Asserts that a handover holds the search's name, its checkpoint, and
    each line up to that checkpoint's iteration, dropping any after it.
    """
    lines = [*halted.lines(halted.iterations)]

    with halted.iterations.open("a", encoding="utf-8") as appended:
        appended.write(lines[-1])

    handover = SearchHandover.from_run(halted)

    assert (handover.name, handover.iterations) == (halted.name, lines)
    assert handover.checkpoint.frontier.iterations == len(lines)


def test_a_handover_refuses_a_search_at_its_steps(halted: Run):
    """
    Asserts that a search whose checkpoint already holds its steps raises,
    since there is nothing left to continue.
    """
    settings = halted.settings.model_copy(update={"steps": 1})

    with raises(ValueError, match="already holds the search's end"):
        SearchHandover.from_run(halted.model_copy(update={"settings": settings}))


def test_a_handover_refuses_a_search_holding_its_goal(
    searcher: Callable[..., Searcher]
):
    """
    Asserts that a search whose checkpoint holds the run's goal raises,
    however many steps it has left.
    """
    run = finish(searcher(steps=100_000))

    with raises(ValueError, match="already holds the search's end"):
        SearchHandover.from_run(run)


def test_a_handover_refuses_a_search_holding_no_checkpoint(halted: Run):
    """
    Asserts that a search holding no checkpoint raises, naming the file.
    """
    halted.checkpoint.unlink()

    with raises(FileNotFoundError, match="checkpoint.npz"):
        SearchHandover.from_run(halted)


def test_a_handover_refuses_a_training_run(run: Run):
    """
    Asserts that a training run hands nothing over to a search, naming the
    command that continues one.
    """
    with raises(ValueError, match="squirtl train"):
        SearchHandover.from_run(run)


def test_a_handover_refuses_iterations_short_of_the_checkpoint(halted: Run):
    """
    Asserts that a search whose iterations end short of its checkpoint
    raises, naming how far each goes.
    """
    halted.iterations.write_text("", encoding="utf-8")

    with raises(
        ValueError,
        match = r"iterations.jsonl holds 0 lines, short of the \d+ the"
    ):
        SearchHandover.from_run(halted)


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
    pools    : list[PoolStandIn],
    searcher : Callable[..., Searcher]
):
    """
    Asserts that the search builds its pool with the workers its settings
    name, spawned rather than forked, each booted on the run's environment.
    """
    built = searcher()

    arguments = pools[-1].arguments

    assert (arguments["max_workers"], arguments["initializer"]) == (
        built.run.settings.search.workers, boot
    )
    assert arguments["mp_context"].get_start_method() == "spawn"
    assert arguments["initargs"] == (built.specification,)


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


def test_a_search_reaching_its_goal_ends_writing_the_path_as_an_episode(
    searcher: Callable[..., Searcher]
):
    """
    Asserts that a search whose presses reach the run's goal ends well short
    of its steps, and writes the path its winner took as the one episode of
    its `episodes`, which reaches the goal from Blue's bedroom and earns the
    winner's reward beside the novelty of each position it passes.
    """
    built = searcher(steps=100_000)
    run   = finish(built)

    [episode] = run.recorded

    assert (built.search.reached, built.step < 100_000) == (True, True)
    assert (
        episode.recording, episode.length,
        run.settings.environment.goal in episode.flags,
        episode.reward > built.search.winner.reward
    ) == (
        built.search.demonstration,
        len(built.search.demonstration.presses),
        True, True
    )


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
    the winner, tree, networks, and lines of one taken through in one go,
    apart from the wall time each line took, and that it records the search
    it resumes.
    """
    unbroken = finish(searcher())
    stopped  = finish(searcher(), stop_at_thirty)
    resumed  = finish(searcher(resumes=stopped))

    assert lines(unbroken) == lines(resumed)
    assert resumed.resumes == stopped.name
    assert_same_checkpoint(
        SearchCheckpoint.from_path(unbroken.checkpoint),
        SearchCheckpoint.from_path(resumed.checkpoint)
    )


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
        f"after {built.search.iterations:,} iterations on finding {run.stop}" in message
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
    Asserts that a line holds no loss where its iteration owed no update
    of the predictor, its presses crossing no multiple of `update_steps`,
    whereas one owing an update holds a loss.
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
    owed  = [
        line.presses // 12 > before.presses // 12
        for before, line in pairwise([Iteration.model_construct(presses=0), *lines])
    ]

    assert [line.loss is not None for line in lines] == owed
    assert {*owed} == {False, True}


def test_each_iteration_writes_a_line_and_the_path_it_leaves(
    searcher: Callable[..., Searcher]
):
    """
    Asserts that every iteration writes one line counting its presses, tree,
    path, wall time, and memory, the last line's length that of the winner's
    path and its reward the winner's.
    """
    built = searcher()
    lines = iterations(finish(built))

    assert len(lines) == built.search.iterations > 1
    assert [line.presses for line in lines] == sorted(line.presses for line in lines)
    assert all(
        line.seconds > 0.0 and line.memory > 0 and line.nodes > 0 for line in lines
    )
    assert (
        lines[-1].presses,
        lines[-1].reward
    ) == (built.step, built.search.winner.reward)
    assert lines[-1].length == len(built.search.demonstration.presses)
