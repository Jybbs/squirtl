"""
Pins the training loop of one run on the CPU, covering:

- The line each finished episode writes, a terminated one's included, the
  episode the run's end cuts short and leaves out, and the updates an
  episode's line averages
- The checkpoint at the first episode end past each interval and at the
  run's end
- A `stop` file, an interrupt, or a termination signal ending the run at an
  episode's end, a second interrupt ending it at once, and the signal
  handlers the loop puts back
- A run stopped halfway and resumed ending with the weights and the lines
  of a run that never stopped, and the lines a resume drops past its
  checkpoint
"""

from collections.abc import Callable
from common.console  import set_event
from pytest          import MonkeyPatch, mark, param, raises
from signal          import SIGINT, SIGTERM, getsignal, raise_signal
from torch.testing   import assert_close

from squirtl.agent.schemas  import Checkpoint
from squirtl.reward.schemas import Event, RewardSettings, Term
from squirtl.runs.schemas   import Run
from squirtl.runs.trainer   import Trainer


def finish(
    trainer : Trainer,
    stop    : Callable[[int, Trainer], None] = lambda *_: None
) -> Run:
    """
    Runs `trainer` to its end, calling `stop` with the step count and the
    trainer after each step it takes.

    Returns:
        The run it trained.
    """
    with trainer:
        for step in trainer:
            stop(step, trainer)

    return trainer.run


def stop_at_eight(step: int, trainer: Trainer):
    """
    Writes the run's `stop` file once `trainer` takes its eighth step.
    """
    if step == 8:
        trainer.run.stop.touch()


@mark.parametrize(
    ("interval", "written"),
    [
        param(10, [12, 20],        id="past-an-interval"),
        param(6,  [6, 12, 18, 20], id="on-each-interval")
    ]
)
def test_a_checkpoint_lands_at_the_first_episode_end_past_each_interval_and_the_end(
    interval    : int,
    monkeypatch : MonkeyPatch,
    trainer     : Callable[..., Trainer],
    written     : list[int]
):
    """
    Asserts that a 20-step run of 6-step episodes writes a checkpoint at the
    first episode end reaching each interval and at its end, at steps 12 and
    20 for an interval of 10 steps, and at every episode end and the end for
    an interval of 6.
    """
    built    = trainer(checkpoint_steps=interval)
    steps    = []
    original = built.checkpoint
    monkeypatch.setattr(
        built,
        "checkpoint",
        lambda: steps.append(built.agent.step) or original()
    )

    finish(built)

    assert (steps, Checkpoint.from_path(built.run.checkpoint).step) == (written, 20)


def test_a_resume_drops_the_lines_past_the_checkpoint_it_continues_from(
    trainer: Callable[..., Trainer]
):
    """
    Asserts that resuming a run whose `episodes` runs past its checkpoint,
    as a run ended at once leaves it, copies the lines up to the checkpoint
    alone, so the resumed run counts each episode once.
    """
    stopped = finish(trainer(), stop_at_eight)
    lines   = stopped.episodes.read_text(encoding="utf-8").splitlines(True)

    with stopped.episodes.open("a", encoding="utf-8") as appended:
        appended.write(lines[0])

    resumed = trainer(resumes=stopped.name)
    resumed.resume(Checkpoint.from_path(stopped.checkpoint), stopped)

    assert (resumed.finished, resumed.run.episodes.read_text(encoding="utf-8")) == (
        2,
        "".join(lines[:2])
    )


def test_a_run_stopped_halfway_and_resumed_ends_as_a_run_that_never_stopped(
    trainer: Callable[..., Trainer]
):
    """
    Asserts that a run stopped at the end of its episode on step 12 and
    resumed to step 20 ends with the networks, Adam's state, replay memory,
    and generators of the same run taken through in one go, and records the
    same episodes, every `timer_div` and press included, apart from the wall
    time each took.
    """
    unbroken = finish(trainer())
    stopped  = finish(trainer(), stop_at_eight)
    resumed  = trainer(resumes=stopped.name)
    resumed.resume(Checkpoint.from_path(stopped.checkpoint), stopped)
    finish(resumed)

    first, second = (
        Checkpoint.from_path(run.checkpoint) for run in (unbroken, resumed.run)
    )

    assert_close(
        [first.online, first.target, first.optimizer, first.replay],
        [second.online, second.target, second.optimizer, second.replay],
        atol = 0,
        rtol = 0
    )
    assert (first.exploration, first.sampling, first.step) == (
        second.exploration, second.sampling, second.step
    )
    unbroken_lines, resumed_lines = (
        [episode.model_dump(exclude={"seconds"}) for episode in run.recorded]
        for run in (unbroken, resumed.run)
    )

    assert unbroken_lines == resumed_lines


def test_a_second_interrupt_ends_the_run_at_once(trainer: Callable[..., Trainer]):
    """
    Asserts that a second interrupt raises `KeyboardInterrupt` on the step
    it lands on, ending the run before its first episode ends and writing
    no checkpoint.
    """
    built = trainer()

    with raises(KeyboardInterrupt):
        finish(built, lambda *_: raise_signal(SIGINT))

    assert (built.agent.step, built.run.checkpoint.exists()) == (2, False)


@mark.parametrize(
    "number",
    [param(SIGINT, id="an-interrupt"), param(SIGTERM, id="a-termination-signal")]
)
def test_a_signal_ends_the_run_at_the_end_of_its_episode(
    number  : int,
    trainer : Callable[..., Trainer]
):
    """
    Asserts that an interrupt or a termination signal on step 3 ends the run
    at the end of its first episode, on step 6, with a checkpoint there.
    """
    run = finish(trainer(), lambda step, _: step == 3 and raise_signal(number))

    assert Checkpoint.from_path(run.checkpoint).step == 6


def test_a_stop_file_ends_the_run_at_the_end_of_its_episode(
    trainer: Callable[..., Trainer]
):
    """
    Asserts that a `stop` file written on step 8 ends the run at the end of
    its episode on step 12, with that episode's line and a checkpoint there.
    """
    run = finish(trainer(), stop_at_eight)

    assert (
        len(list(run.recorded)),
        Checkpoint.from_path(run.checkpoint).step
    ) == (2, 12)


def test_an_episode_reaching_the_starter_writes_a_terminated_line(
    trainer: Callable[..., Trainer]
):
    """
    Asserts that an episode whose step sets the starter's flag ends there,
    its line recording its three steps, its termination, and the starter's
    pay, and that the next episode starts afresh from the state the reset
    loads.
    """
    run = finish(
        trainer = trainer(),
        stop    = lambda step, trainer: step == 2
        and set_event(
            Event.EVENT_GOT_STARTER,
            trainer.env.unwrapped.game_boy.emulator.memory
        )
    )
    recorded = list(run.recorded)

    assert [(episode.length, episode.terminated) for episode in recorded] == [
        (3, True),
        (6, False),
        (6, False)
    ]
    assert recorded[0].shares[Term.STARTER] == RewardSettings().starter


@mark.parametrize(
    "steps",
    [param(20, id="two-steps-cut-off"), param(18, id="ending-as-the-third-ends")]
)
def test_each_finished_episode_writes_a_line_and_the_cut_one_none(
    steps   : int,
    trainer : Callable[..., Trainer]
):
    """
    Asserts that a run of 6-step episodes writes a line for each of the
    three its time limit truncated, each holding its six presses, whether
    its end cuts two steps of a fourth off or lands on the third's last
    step.
    """
    assert [
        (episode.length, episode.terminated, len(episode.recording.presses))
        for episode in finish(trainer(steps=steps)).recorded
    ] == [(6, False, 6)] * 3


def test_an_episodes_line_averages_the_updates_its_steps_took(
    trainer: Callable[..., Trainer]
):
    """
    Asserts that the first episode's line holds no loss or value, since its
    six transitions fall short of a batch of eight, whereas each line after
    it holds both.
    """
    assert [
        (episode.loss is None, episode.value is None)
        for episode in finish(trainer()).recorded
    ] == [
        (True, True),
        (False, False),
        (False, False)
    ]


def test_the_run_puts_each_signals_handler_back_once_it_ends(
    trainer: Callable[..., Trainer]
):
    """
    Asserts that the interrupt and termination signals take back the
    handlers they held before the run began, once the run ends.
    """
    handlers = [getsignal(number) for number in (SIGINT, SIGTERM)]
    finish(trainer())

    assert [getsignal(number) for number in (SIGINT, SIGTERM)] == handlers
