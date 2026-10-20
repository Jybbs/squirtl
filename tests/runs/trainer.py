"""
Pins the training loop of one run on the CPU, covering:

- The line each finished episode writes, a terminated one's included, the
  episode the run's end cuts short and leaves out, and the return, the
  positions, the chance of a random action, and the update means each line
  holds
- The checkpoint at the first episode end reaching each interval and at
  the run's end, a resumed run counting the interval on from its checkpoint
- A `stop` file, logged once found, an interrupt, or a termination signal
  ending the run at an episode's end, a second interrupt ending it at once,
  and the signal handlers the loop puts back
- A run stopped halfway and resumed ending with the weights and the lines
  of a run that never stopped, and the lines a resume drops past its
  checkpoint
- The evaluation at the first episode end reaching each interval, which
  leaves the training as it was and logs what each policy reached, and the
  evaluations and the baseline a resume copies up to its checkpoint
"""

from collections.abc   import Callable
from common.console    import set_event, stand
from common.evaluation import EvaluatorStandIn, played
from pytest            import MonkeyPatch, approx, mark, param, raises
from signal            import SIGINT, SIGTERM, getsignal, raise_signal
from torch.testing     import assert_close

from squirtl.agent.schemas      import AgentSettings, Checkpoint, Update
from squirtl.evaluation.schemas import Evaluation, EvaluationSettings
from squirtl.reward.schemas     import Event, Position, RewardSettings, Term
from squirtl.runs.schemas       import Run
from squirtl.runs.trainer       import Trainer


def checkpoints(monkeypatch: MonkeyPatch, trainer: Trainer) -> list[int]:
    """
    Makes each checkpoint `trainer` writes record the step it lands at
    before writing it.

    Returns:
        The steps, in the order the checkpoints land.
    """
    steps   = []
    written = trainer.checkpoint
    monkeypatch.setattr(
        trainer,
        "checkpoint",
        lambda: steps.append(trainer.agent.step) or written()
    )

    return steps


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
def test_a_checkpoint_lands_at_the_first_episode_end_reaching_each_interval_and_the_end(
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
    built = trainer(checkpoint_steps=interval)
    steps = checkpoints(monkeypatch, built)

    finish(built)

    assert (steps, Checkpoint.from_path(built.run.checkpoint).step) == (written, 20)


def test_a_resume_copies_the_evaluations_up_to_its_checkpoint_and_the_baseline(
    evaluators : list[EvaluatorStandIn],
    trainer    : Callable[..., Trainer]
):
    """
    Asserts that resuming a run evaluated at step 12, whose `evaluations`
    runs past its checkpoint there, copies the evaluation at step 12 and the
    baseline alone, so the resumed run plays only its evaluation at step 20
    and ends holding the evaluations of a run that never stopped.
    """
    stopped = finish(trainer(evaluation_steps=10), stop_at_eight)
    stopped.append(stopped.evaluations, played([0.5], 18))
    resumed = trainer(evaluation_steps=10, resumes=stopped)
    resumed_files, unbroken_files = (
        [path.read_text(encoding="utf-8") for path in (run.evaluations, run.baseline)]
        for run in (finish(resumed), finish(trainer(evaluation_steps=10)))
    )

    assert resumed_files == unbroken_files
    assert [stand_in.asked for stand_in in evaluators] == [
        [12, None],
        [20],
        [12, None],
        [20]
    ]


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

    resumed = trainer(resumes=stopped)

    assert (resumed.finished, resumed.run.episodes.read_text(encoding="utf-8")) == (
        2,
        "".join(lines[:2])
    )


def test_a_resumed_run_writes_its_checkpoints_where_a_run_that_never_stopped_does(
    monkeypatch : MonkeyPatch,
    trainer     : Callable[..., Trainer]
):
    """
    Asserts that a run stopped on step 12 writes a checkpoint there and its
    resumption one at step 20, the steps the same run taken through in one
    go writes them at, the resumed run counting its next interval on from
    step 12.
    """
    unbroken, stopped = trainer(), trainer()
    steps = [checkpoints(monkeypatch, built) for built in (unbroken, stopped)]
    finish(unbroken)
    finish(stopped, stop_at_eight)
    resumed = trainer(resumes=stopped.run)
    steps.append(checkpoints(monkeypatch, resumed))
    finish(resumed)

    assert steps == [[12, 20], [12], [20]]


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
    resumed  = trainer(resumes=finish(trainer(), stop_at_eight))
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


def test_a_stop_file_ends_the_run_at_the_end_of_its_episode(
    logged  : list[str],
    trainer : Callable[..., Trainer]
):
    """
    Asserts that a `stop` file written on step 8 ends the run at the end of
    its episode on step 12, with that episode's line and a checkpoint there,
    and logs the file it found.
    """
    run = finish(trainer(), stop_at_eight)

    assert (
        len(list(run.recorded)),
        Checkpoint.from_path(run.checkpoint).step
    ) == (2, 12)
    assert f"Stopping at the end of episode 2 on finding {run.stop}" in logged


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


def test_an_episodes_line_records_its_return_positions_epsilon_and_update_means(
    logged      : list[str],
    monkeypatch : MonkeyPatch,
    trainer     : Callable[..., Trainer]
):
    """
    Asserts that each line holds the return its steps earned, the positions
    it reached, the chance of a random action at its last step, and the
    mean loss and value of the updates its steps took, which the line
    each episode logs repeats as label and value pairs, the first episode
    stepping onto a new square on its second step and reaching the starter
    on its third. The chance falls by 0.05 a step and the novelty pays
    0.0625, leaving each value the line logs clear of a tie at the places it
    rounds to.
    """
    reward = RewardSettings(novelty=0.0625)
    built  = trainer(
        agent = AgentSettings(
            batch_size           = 8,
            capacity             = 64,
            device               = "cpu",
            epsilon_end          = 0.0,
            exploration_fraction = 1.0
        ),
        reward = reward
    )
    monkeypatch.setattr(
        built.agent,
        "update",
        lambda: Update(loss=built.agent.step, value=-built.agent.step)
    )

    def move_then_choose(step: int, trainer: Trainer):
        """
        Stands the player on a new square after the first step and sets the
        starter's flag after the second.
        """
        memory = trainer.env.unwrapped.game_boy.emulator.memory

        if step == 1:
            stand(memory, Position(map=1, x=1, y=1))

        if step == 2:
            set_event(Event.EVENT_GOT_STARTER, memory)

    assert [
        (
            episode.reward, episode.positions, episode.epsilon,
            episode.loss, episode.value
        )
        for episode in finish(built, move_then_choose).recorded
    ] == [
        (approx(reward.novelty + reward.starter), 2, approx(0.85), 2.0, -2.0),
        (0.0, 1, approx(0.55), 6.5, -6.5),
        (0.0, 1, approx(0.25), 12.5, -12.5)
    ]
    assert [
        message.partition(": ")[2]
        for message in logged if message.startswith("Episode ")
    ] == [
        "return 0.6625, positions 2, epsilon 0.850, loss 2, value -2",
        "return 0.0000, positions 1, epsilon 0.550, loss 6.5, value -6.5",
        "return 0.0000, positions 1, epsilon 0.250, loss 12.5, value -12.5"
    ]


@mark.parametrize(
    ("interval", "asked"),
    [
        param(10, [[12, None], [20]],      id="past-an-interval"),
        param(6,  [[6, None], [12], [18]], id="on-each-interval")
    ]
)
def test_an_evaluation_lands_at_the_first_episode_end_reaching_each_interval(
    asked      : list[list[int | None]],
    evaluators : list[EvaluatorStandIn],
    interval   : int,
    trainer    : Callable[..., Trainer]
):
    """
    Asserts that a 20-step run of 6-step episodes evaluates the agent where
    an episode end or the run's last step first reaches each interval, at
    steps 12 and 20 for an interval of 10 and at every episode end for an
    interval of 6, playing the baseline at its first evaluation alone.
    """
    finish(trainer(evaluation_steps=interval))

    assert [stand_in.asked for stand_in in evaluators] == asked


@mark.usefixtures("evaluators")
def test_an_evaluation_logs_how_often_each_policy_reached_the_starter(
    logged  : list[str],
    trainer : Callable[..., Trainer]
):
    """
    Asserts that an evaluation at step 12 logs its start, then the share
    of episodes in which the agent and the random baseline each reached the
    starter beside each one's mean return, from the stand-in's returns of
    0.012 and 0.125.
    """
    finish(trainer(evaluation_steps=10))

    assert {
        "At step 12, the agent reached the starter in 0% of its evaluation episodes "
        "for a mean return of 0.0120, and the random baseline in 0% for 0.1250",
        "Evaluating the agent at step 12"
    } <= set(logged)


def test_an_evaluation_writes_its_episodes_and_leaves_the_training_as_it_was(
    trainer: Callable[..., Trainer]
):
    """
    Asserts that a run evaluating at steps 12 and 20 over two episodes in
    two worker processes writes the agent's evaluations and the baseline's,
    and ends with the networks, Adam's state, replay memory, generators, and
    episodes of the same run evaluating nothing.
    """
    evaluated = finish(
        trainer = trainer(
            evaluation       = EvaluationSettings(environments=2, episodes=2),
            evaluation_steps = 10
        )
    )
    plain         = finish(trainer())
    first, second = (Checkpoint.from_path(run.checkpoint) for run in (evaluated, plain))
    evaluated_lines, plain_lines = (
        [episode.model_dump(exclude={"seconds"}) for episode in run.recorded]
        for run in (evaluated, plain)
    )

    assert_close(
        [first.online, first.target, first.optimizer, first.replay],
        [second.online, second.target, second.optimizer, second.replay],
        atol = 0,
        rtol = 0
    )
    assert (first.exploration, first.sampling) == (second.exploration, second.sampling)
    assert evaluated_lines == plain_lines
    assert [
        (
            evaluation.step,
            len(evaluation.outcomes)
        ) for evaluation in evaluated.evaluated
    ] == [(12, 2), (20, 2)]
    assert Evaluation.model_validate_json(
        evaluated.baseline.read_text(encoding="utf-8")
    ).step is None


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
