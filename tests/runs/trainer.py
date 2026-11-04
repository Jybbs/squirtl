"""
Pins the training loop of one run on the CPU, covering:

- The line each finished episode writes, a terminated one's included, the
  episode the run's end cuts short and leaves out, and the return, the
  positions, the chance of a random action, and the update means each line
  holds
- The checkpoint at the first episode end reaching each interval and at
  the run's end, each written after the episodes are flushed to disk, and
  a resumed run counting the interval on from its checkpoint
- A `stop` file, logged once found, an interrupt, or a termination signal
  ending the run at an episode's end, a second interrupt ending it at once,
  and the signal handlers the loop puts back
- A run stopped halfway and resumed ending with the weights and the lines
  of a run that never stopped, and the lines a resume drops past its
  checkpoint
- The evaluation at the first episode end reaching each interval, which
  leaves the training as it was and logs what each policy reached, and the
  evaluations and the baseline a resume copies up to its checkpoint
- PQN's and PPO's run across environments, meaning the environments its
  settings name, the reset each starts from, the workers an interrupt leaves
  stepping, a run of one environment, the rollout a run's last step falls
  within, the line each episode writes as its step returns, its measures
  averaged over the updates taken while it played, the value of each
  truncated episode's final observation, the stop, the checkpoint, and the
  evaluation landing as a rollout's update ends, and a resume ending as a
  run that never stopped wherever it stopped
"""

from collections.abc   import Callable
from common.agents     import each_agent
from common.console    import set_event, stand
from common.evaluation import EvaluatorStandIn, played
from datetime          import UTC, datetime
from gymnasium.spaces  import Box, Dict
from gymnasium.vector  import AutoresetMode
from itertools         import count
from numpy             import array, full, ndarray, uint8
from os                import kill
from pytest            import MonkeyPatch, approx, mark, param, raises
from signal            import SIGINT, SIGTERM, getsignal, raise_signal
from torch.testing     import assert_close
from types             import SimpleNamespace

from squirtl.agent.schemas       import AgentSettings, Algorithm, Measures, PolicyUpdate, ReplayCheckpoint, Update
from squirtl.emulator.schemas    import Cartridge
from squirtl.environment.schemas import EnvironmentSettings
from squirtl.evaluation.schemas  import Evaluation, EvaluationSettings
from squirtl.reward.schemas      import Event, Position, RewardSettings, Term
from squirtl.runs.schemas        import Run, RunSettings, VectorCheckpoint
from squirtl.runs.trainer        import EpisodeTrainer, RolloutTrainer, Tally, Trainer


def assert_ended_alike(resumed: Run, unbroken: Run):
    """
    Asserts that `resumed` ends with the network, the optimizer, the
    generators, the statistics, and each environment's slot of `unbroken`,
    and records the same episodes apart from the wall time each took.
    """
    first, second = (VectorCheckpoint.from_path(run.checkpoint) for run in (
        unbroken, resumed
    ))

    assert_close(
        [first.online, first.optimizer],
        [second.online, second.optimizer],
        atol = 0,
        rtol = 0
    )
    assert first.model_dump(exclude={"online", "optimizer"}) == second.model_dump(
        exclude = {"online", "optimizer"}
    )
    assert [line.model_dump(exclude={"seconds"}) for line in unbroken.recorded] == [
        line.model_dump(exclude={"seconds"}) for line in resumed.recorded
    ]


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


def replace_updates(
    measures    : Callable[[int], Measures],
    monkeypatch : MonkeyPatch,
    trainer     : Trainer
):
    """
    Makes each update of `trainer`'s agent report `measures` of its number,
    counting from 1, once the update has run.
    """
    numbers = count(1)
    update  = trainer.agent.update

    monkeypatch.setattr(
        trainer.agent,
        "update",
        lambda observations: (update(observations), measures(next(numbers)))[1]
    )


def rewarding(trainer: Trainer) -> Trainer:
    """
    Makes each reward reaching `NormalizeReward` depend on the action taken,
    since the blank cartridge pays none.

    Returns:
        The trainer.
    """
    step = trainer.env.env.step

    def rewarded(actions: ndarray) -> tuple[object, ...]:
        """
        Steps the environments, adding an eighth of each action to its
        reward.
        """
        observations, rewards, *ends = step(actions)

        return observations, rewards + actions / 8, *ends

    trainer.env.env.step = rewarded

    return trainer


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

    assert steps == written
    assert steps[-1] == ReplayCheckpoint.from_path(built.run.checkpoint).step


def stop_at_eight(step: int, trainer: Trainer):
    """
    Writes the run's `stop` file once `trainer` takes its eighth step.
    """
    if step == 8:
        trainer.run.stop.touch()


def test_a_checkpoint_and_an_evaluation_land_where_an_update_reaches_each_interval(
    evaluators  : list[EvaluatorStandIn],
    monkeypatch : MonkeyPatch,
    rolling     : Callable[..., Trainer]
):
    """
    Asserts that a run of 8-sample rollouts writes a checkpoint and
    evaluates the agent at steps 16, 24, and 32, the ends of the updates
    first reaching each multiple of 10 since the last, and no further
    checkpoint at its end.
    """
    trainer = rolling(Algorithm.PQN, checkpoint_steps=10, evaluation_steps=10)
    steps   = checkpoints(monkeypatch, trainer)
    finish(trainer)

    assert steps == [16, 24, 32]
    assert steps[-1] == VectorCheckpoint.from_path(trainer.run.checkpoint).step
    assert [stand_in.asked for stand_in in evaluators] == [[16, None], [24], [32]]
    assert evaluators[0].arguments[0] is Algorithm.PQN


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

    assert ReplayCheckpoint.from_path(run.checkpoint).step == 6


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


def test_a_rollout_run_makes_the_environments_its_settings_name(
    rolling: Callable[..., Trainer]
):
    """
    Asserts that a run of PQN or PPO makes as many environments as
    its settings count, at most `max_concurrency` of them stepping at
    once, each reporting an episode's final observation on its last
    step, and normalizes rewards at the run's discount rather than at
    `NormalizeReward`'s own.
    """
    with rolling(Algorithm.PPO, agent={"discount": 0.9, "max_concurrency": 1}) as run:
        vector = run.env.unwrapped

        assert (
            run.env.gamma, vector.autoreset_mode,
            vector.max_concurrency, vector.num_envs
        ) == (0.9, AutoresetMode.SAME_STEP, 1, 2)


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


def test_a_rollout_run_of_one_environment_writes_a_line_for_each_episode(
    rolling: Callable[..., Trainer]
):
    """
    Asserts that a run of one environment, which counts a step at a time,
    reaches its last step and writes a line for each of the two episodes it
    truncates by then.
    """
    run = finish(
        trainer = rolling(
            Algorithm.PPO,
            agent       = {"environments": 1},
            environment = EnvironmentSettings(max_episode_steps=3),
            steps       = 8
        )
    )

    assert VectorCheckpoint.from_path(run.checkpoint).step == 8
    assert len(list(run.recorded)) == 2


def test_a_rollout_run_resuming_a_checkpoint_of_another_agent_is_refused(
    rolling: Callable[..., Trainer]
):
    """
    Asserts that a checkpoint of PQN refuses to restore into a run of PPO,
    naming the mismatch before the run makes any directory.
    """
    stopped = finish(rolling(Algorithm.PQN, steps=8))

    with raises(ValueError, match="checkpoint"):
        rolling(
            Algorithm.PPO,
            resumes = stopped.model_copy(
                update = {"settings": stopped.settings.model_copy(update={"steps": 32})}
            )
        )


def test_a_run_remembers_the_value_of_a_final_observation_at_the_step_truncating_it(
    monkeypatch : MonkeyPatch,
    rolling     : Callable[..., Trainer]
):
    """
    Asserts that a run hands the agent 0 on every step but the sixth, which
    truncates both environments' episodes and carries the value of each
    one's final observation.
    """
    trainer  = rolling(Algorithm.PQN, steps=16)
    remember = trainer.agent.remember
    seen     = []
    monkeypatch.setattr(
        trainer.agent,
        "remember",
        lambda bootstraps, *outcome: seen.append(bootstraps.tolist()) or remember(
            bootstraps,
            *outcome
        )
    )
    monkeypatch.setattr(
        trainer.agent,
        "value",
        lambda observations: full(len(observations["frames"]), 7.0)
    )
    finish(trainer)

    assert seen == [[0.0, 0.0]] * 5 + [[7.0, 7.0]] + [[0.0, 0.0]] * 2


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
        ReplayCheckpoint.from_path(run.checkpoint) for run in (unbroken, resumed.run)
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
        ReplayCheckpoint.from_path(run.checkpoint).step
    ) == (2, 12)
    assert f"Stopping at step 12 after 2 episodes on finding {run.stop}" in logged


def test_a_tally_averages_each_environments_updates_until_its_episode_ends():
    """
    Asserts that a tally reads the mean of each measure of the updates added
    since the environment's last episode ended, and `None` where none was,
    each environment on its own count.
    """
    tally = Tally(2, Update)
    tally.add(Update(loss=1.0, value=2.0))
    tally.add(Update(loss=3.0, value=4.0))

    assert tally.take(0) == Update(loss=2.0, value=3.0)
    assert tally.take(0) is None

    tally.add(Update(loss=8.0, value=9.0))

    assert tally.take(0) == Update(loss=8.0, value=9.0)
    assert tally.take(1) == Update(loss=4.0, value=5.0)


@mark.parametrize(
    ("algorithm", "kind"),
    [
        param(Algorithm.DQN, EpisodeTrainer, id="the-deep-q-network"),
        param(Algorithm.PPO, RolloutTrainer, id="ppo"),
        param(Algorithm.PQN, RolloutTrainer, id="pqn")
    ]
)
def test_the_settings_start_the_training_loop_of_the_agent_they_name(
    algorithm   : Algorithm,
    cartridge   : Cartridge,
    kind        : type[Trainer],
    monkeypatch : MonkeyPatch
):
    """
    Asserts that a run starts the loop of one environment for the deep
    Q-network and the loop across environments for PQN and PPO.
    """
    monkeypatch.setattr(Trainer, "__init__", lambda trainer, *arguments: None)
    monkeypatch.setattr(RolloutTrainer, "__init__", lambda trainer, *arguments: None)
    settings = RunSettings(agent=AgentSettings(algorithm=algorithm))

    assert type(Trainer.start(cartridge, settings, datetime.now(UTC))) is kind


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


@each_agent
def test_each_environments_episode_writes_a_line_as_its_last_step_returns(
    algorithm : Algorithm,
    rolling   : Callable[..., Trainer]
):
    """
    Asserts that a run of 32 steps across two environments writes a line per
    environment at each environment's sixth and twelfth steps, each holding
    six presses, leaves out the episodes its last step cuts short, and
    carries the measures of its agent, an epsilon for PQN and none for PPO.
    """
    lines = list(finish(rolling(algorithm)).recorded)

    assert [(
        line.length,
        len(line.recording.presses)
    ) for line in lines] == [(6, 6)] * 4
    assert {type(line.update) for line in lines} == {algorithm.measures}
    assert {line.epsilon is None for line in lines} == {algorithm.sampled}


@mark.parametrize(
    ("limit", "means", "steps"),
    [
        param(3,  [None, 1.0], 16, id="an-episode-ending-before-the-first-update"),
        param(10, [1.5, 3.5],  40, id="an-episode-spanning-two-updates")
    ]
)
def test_an_episodes_line_averages_the_updates_taken_while_it_played(
    limit       : int,
    means       : list[float | None],
    monkeypatch : MonkeyPatch,
    rolling     : Callable[..., Trainer],
    steps       : int
):
    """
    Asserts that each line averages the updates that ended between the
    episode's first step and its last, an update numbered from 1 reporting
    its number as its loss, so that the update of the rollout an episode
    ends in counts toward the next episode.
    """
    trainer = rolling(
        Algorithm.PQN,
        environment = EnvironmentSettings(max_episode_steps=limit),
        steps       = steps
    )
    replace_updates(lambda number: Update(loss=number, value=0.0), monkeypatch, trainer)
    lines = list(finish(trainer).recorded)

    assert [line.update and line.update.loss for line in lines[::2]] == means


def test_an_episodes_line_averages_the_updates_its_steps_took(
    trainer: Callable[..., Trainer]
):
    """
    Asserts that the first episode's line holds no loss or value, since its
    six steps fall short of the warm-up of eight, whereas each line after it
    holds both, the second from its updates at steps 8 and 12 and the third
    from its update at step 16.
    """
    assert [
        episode.update is None for episode in finish(trainer()).recorded
    ] == [True, False, False]


@mark.parametrize(
    ("finals", "truncated", "values"),
    [
        param(None, [False, False], [0.0, 0.0], id="no-episode-ended"),
        param(
            array([None, {"frames": full((1, 2), 7, uint8)}], object),
            [False, False],
            [0.0, 0.0],
            id = "an-episode-terminated"
        ),
        param(
            array([None, {"frames": full((1, 2), 7, uint8)}], object),
            [False, True],
            [0.0, 7.0],
            id = "an-episode-truncated"
        )
    ]
)
def test_a_step_values_the_final_observation_of_each_episode_it_truncated(
    finals    : ndarray | None,
    truncated : list[bool],
    values    : list[float]
):
    """
    Asserts that a truncated episode's slot takes the value of the final
    observation, batched as the agent's network reads one, and that every
    other slot takes 0, a terminated episode's included.
    """
    stand_in = SimpleNamespace(
        agent = SimpleNamespace(
            value = lambda observations: observations["frames"].max(axis=(1, 2))
        ),
        env = SimpleNamespace(
            single_observation_space = Dict(frames=Box(0, 255, (1, 2), uint8))
        )
    )

    assert RolloutTrainer.bootstraps(
        stand_in,
        finals,
        array(truncated)
    ).tolist() == values


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
        (episode.reward, episode.positions, episode.epsilon, episode.update)
        for episode in finish(built, move_then_choose).recorded
    ] == [
        (
            approx(reward.novelty + reward.starter),
            2,
            approx(0.85),
            Update(loss=2.0, value=-2.0)
        ),
        (0.0, 1, approx(0.55), Update(loss=6.5, value=-6.5)),
        (0.0, 1, approx(0.25), Update(loss=12.5, value=-12.5))
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
    ("stop", "message"),
    [
        param(
            lambda trainer: trainer.run.stop.touch(),
            "Stopping at step 16 after 2 episodes on finding",
            id = "the-stop-file"
        ),
        param(
            lambda trainer: raise_signal(SIGINT),
            "Stopping at the end of the rollout's update",
            id = "an-interrupt"
        ),
        param(
            lambda trainer: raise_signal(SIGTERM),
            "Stopping at the end of the rollout's update",
            id = "a-termination-signal"
        )
    ]
)
def test_a_stop_within_a_rollout_ends_the_run_once_its_update_ends(
    logged  : list[str],
    message : str,
    rolling : Callable[..., Trainer],
    stop    : Callable[[Trainer], None]
):
    """
    Asserts that a stop on step 10, inside the second rollout, plays that
    rollout out and writes the checkpoint at step 16 once its update ends,
    logging where the run stops.
    """
    run = finish(
        trainer = rolling(Algorithm.PQN),
        stop    = lambda step, trainer: step == 10 and stop(trainer)
    )

    assert (
        len(list(run.recorded)),
        VectorCheckpoint.from_path(run.checkpoint).step
    ) == (2, 16)
    assert any(line.startswith(message) for line in logged)


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
    first, second = (ReplayCheckpoint.from_path(run.checkpoint) for run in (
        evaluated, plain
    ))
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


@each_agent
def test_a_rollout_checkpoint_holds_where_each_environment_stands(
    algorithm : Algorithm,
    rolling   : Callable[..., Trainer]
):
    """
    Asserts that a checkpoint at step 16 counts the two episodes the run
    wrote and holds each environment two steps into its next, the one update
    taken while that episode played summed for each of its agent's measures,
    beside the statistics scaling each reward.
    """
    checkpoint = VectorCheckpoint.from_path(
        finish(rolling(algorithm, steps=16)).checkpoint
    )

    assert (
        checkpoint.episodes, checkpoint.step,
        checkpoint.moments.count > 16
    ) == (2, 16, True)
    assert [
        (len(slot.recording.presses), slot.count, len(slot.totals))
        for slot in checkpoint.slots
    ] == [(2, 1, len(algorithm.measures.model_fields))] * 2


@each_agent
@mark.parametrize(
    ("limit", "played", "stopped_at"),
    [
        param(6, 2, 10, id="within-its-second-rollout"),
        param(6, 4, 8,  id="on-its-first-rollouts-last-step"),
        param(4, 0, 8,  id="on-the-step-ending-each-episode")
    ]
)
def test_a_rollout_run_stopped_and_resumed_ends_as_a_run_that_never_stopped(
    algorithm  : Algorithm,
    limit      : int,
    played     : int,
    rolling    : Callable[..., Trainer],
    stopped_at : int
):
    """
    Asserts that a run stopped with each environment `played` steps into
    an episode truncated after `limit`, and resumed to step 32, ends as
    the same run taken through in one go, under rewards that depend on each
    action.
    """
    environment = EnvironmentSettings(max_episode_steps=limit)
    unbroken    = finish(rewarding(rolling(algorithm, environment=environment)))
    stopped     = finish(
        trainer = rewarding(rolling(algorithm, environment=environment)),
        stop    = lambda step, trainer: step == stopped_at and trainer.run.stop.touch()
    )
    resumed = finish(
        trainer = rewarding(
            trainer = rolling(algorithm, environment=environment, resumes=stopped)
        )
    )

    assert [
        len(slot.recording.presses)
        for slot in VectorCheckpoint.from_path(stopped.checkpoint).slots
    ] == [played] * 2
    assert_ended_alike(resumed, unbroken)


@each_agent
def test_a_rollout_run_stopped_before_its_first_step_resumes_as_one_never_stopped(
    algorithm : Algorithm,
    rolling   : Callable[..., Trainer]
):
    """
    Asserts that a run finding its `stop` file before its first step writes
    a checkpoint of no steps, each environment's recording holding no
    presses, from which it resumes as a run that never stopped.
    """
    stopping = rewarding(rolling(algorithm))

    stopping.run.stop.touch()

    stopped    = finish(stopping)
    checkpoint = VectorCheckpoint.from_path(stopped.checkpoint)

    assert (
        checkpoint.step,
        [len(slot.recording.presses) for slot in checkpoint.slots]
    ) == (0, [0, 0])
    assert_ended_alike(
        resumed  = finish(rewarding(rolling(algorithm, resumes=stopped))),
        unbroken = finish(rewarding(rolling(algorithm)))
    )


def test_an_interrupt_reaching_each_worker_leaves_the_rollout_stepping(
    rolling: Callable[..., Trainer]
):
    """
    Asserts that each environment's worker ignores the interrupt a terminal
    sends the whole process group, so the rollout runs on to the step where
    the trainer decides whether to stop.
    """
    with rolling(Algorithm.PQN, steps=8) as trainer:
        for process in trainer.env.unwrapped.processes:
            kill(process.pid, SIGINT)

        assert list(trainer)[-1] == 8


def test_each_checkpoint_follows_the_episodes_written_through_to_disk(
    monkeypatch : MonkeyPatch,
    trainer     : Callable[..., Trainer]
):
    """
    Asserts that a run writes its `episodes` through to disk before each
    checkpoint it saves, at steps 12 and 20, so no checkpoint runs ahead of
    the episodes recorded before it.
    """
    events = []
    sync   = Run.sync
    save   = ReplayCheckpoint.save
    monkeypatch.setattr(
        Run,
        "sync",
        lambda run, path: events.append(path.name) or sync(run, path)
    )
    monkeypatch.setattr(
        ReplayCheckpoint,
        "save",
        lambda checkpoint, path: events.append(path.name) or save(checkpoint, path)
    )
    finish(trainer())

    assert events == ["episodes.jsonl", "checkpoint.npz"] * 2


def test_each_environment_starts_from_a_reset_of_its_own(
    rolling: Callable[..., Trainer]
):
    """
    Asserts that each environment takes a seed of its own at its first
    reset, which leaves the two at different values of `timer_div`.
    """
    with rolling(Algorithm.PQN) as trainer:
        first, second = trainer.env.unwrapped.get_attr("recording")

    assert first.timer_div != second.timer_div


@mark.parametrize(
    ("last", "steps"),
    [param(8, 1, id="within-the-first-rollout"), param(16, 10, id="within-the-second")]
)
def test_a_run_whose_steps_fall_within_a_rollout_plays_that_rollout_out(
    last    : int,
    rolling : Callable[..., Trainer],
    steps   : int
):
    """
    Asserts that a run ends on the last step of the rollout its `steps` fall
    within, since every update reads a full rollout.
    """
    run = finish(rolling(Algorithm.PQN, steps=steps))

    assert VectorCheckpoint.from_path(run.checkpoint).step == last


def test_ppos_episode_logs_no_epsilon_beside_its_measures(
    logged      : list[str],
    monkeypatch : MonkeyPatch,
    rolling     : Callable[..., Trainer]
):
    """
    Asserts that an episode of PPO logs that it holds no epsilon, beside
    each measure under its own name, reading no update where none ran.
    """
    trainer = rolling(Algorithm.PPO, steps=16)
    replace_updates(
        measures = lambda number: PolicyUpdate(
            clipped     = 0.25,
            entropy     = 1.5,
            kl          = 0.01,
            policy_loss = -0.5,
            value_loss  = 3.0
        ),
        monkeypatch = monkeypatch,
        trainer     = trainer
    )
    finish(trainer)

    assert any(
        message.endswith(
            "epsilon none, clipped 0.25, entropy 1.5, kl 0.01, policy_loss -0.5, "
            "value_loss 3"
        )
        for message in logged
    )


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
