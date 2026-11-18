"""
Pins the records a resumed run continues from, covering:

- A checkpoint of PQN or PPO read back as written, a slot holding a recording
  of no presses among them, and the episodes a handover of each takes
- A tally averaging each environment's updates until its episode ends
- The handover a resumed search reads, and the training run, the search at
  its steps or its goal, the missing checkpoint, and the short iterations it
  refuses
"""

from collections.abc     import Callable
from common.agents       import each_agent
from common.search       import finish
from pathlib             import Path
from pytest              import raises
from torch               import tensor
from torch.serialization import get_safe_globals

from squirtl.agent.schemas       import AgentSettings, Algorithm, Update
from squirtl.environment.schemas import Recording
from squirtl.runs.handover       import Moments, SearchHandover, Slot, Tally, VectorCheckpoint
from squirtl.runs.schemas        import Run
from squirtl.runs.searcher       import Searcher
from squirtl.runs.settings       import RunSettings
from squirtl.runs.trainer        import Trainer


def test_a_search_handover_reads_the_lines_its_checkpoint_holds(halted: Run):
    """
    Asserts that a search's handover holds its name, its checkpoint, and
    each line up to that checkpoint's iteration, dropping any after it.
    """
    lines = [*halted.lines(halted.iterations)]

    with halted.iterations.open("a", encoding="utf-8") as appended:
        appended.write(lines[-1])

    handover = SearchHandover.from_run(halted)

    assert (handover.name, handover.iterations) == (halted.name, lines)
    assert handover.checkpoint.frontier.iterations == len(lines)


def test_a_search_handover_refuses_a_search_at_its_steps(halted: Run):
    """
    Asserts that a search whose checkpoint already holds its steps raises,
    since there is nothing left to continue.
    """
    settings = halted.settings.model_copy(update={"steps": 1})

    with raises(ValueError, match="already holds the search's end"):
        SearchHandover.from_run(halted.model_copy(update={"settings": settings}))


def test_a_search_handover_refuses_a_search_holding_its_goal(
    searcher: Callable[..., Searcher]
):
    """
    Asserts that a search whose checkpoint holds the run's goal raises,
    however many steps it has left.
    """
    run = finish(searcher(steps=100_000))

    with raises(ValueError, match="already holds the search's end"):
        SearchHandover.from_run(run)


@each_agent
def test_a_handover_of_pqn_or_ppo_takes_the_episodes_its_checkpoint_counts(
    algorithm : Algorithm,
    holding   : Callable[[str], Run]
):
    """
    Asserts that a run of either agent hands over its checkpoint and the
    count of lines that checkpoint names whatever their lengths, dropping
    the line a run wrote past it.
    """
    lines = ['{"length": 99}\n', '{"length": 99}\n']
    run   = holding("".join(lines)).model_copy(
        update = {"settings": RunSettings(agent=AgentSettings(algorithm=algorithm))}
    )
    vector_checkpoint(1, 16).save(run.checkpoint)
    handover = Trainer.handover(run)

    assert (
        type(handover.checkpoint),
        handover.episodes
    ) == (VectorCheckpoint, lines[:1])


def test_a_search_handover_refuses_a_search_holding_no_checkpoint(halted: Run):
    """
    Asserts that a search holding no checkpoint raises, naming the file.
    """
    halted.checkpoint.unlink()

    with raises(FileNotFoundError, match="checkpoint.npz"):
        SearchHandover.from_run(halted)


def test_a_search_handover_refuses_a_training_run(run: Run):
    """
    Asserts that a training run hands nothing over to a search, naming the
    command that continues one.
    """
    with raises(ValueError, match="squirtl train"):
        SearchHandover.from_run(run)


def test_a_search_handover_refuses_iterations_short_of_the_checkpoint(halted: Run):
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


def test_a_vector_checkpoint_of_a_recording_of_no_presses_reads_back(tmp_path: Path):
    """
    Asserts that a slot whose recording holds no presses reads back as
    written, whose empty `bytes` `torch.save` pickles through the `bytes`
    global, and that the read allows that global for its own `torch.load`
    alone.
    """
    written = vector_checkpoint(2, 16, presses=b"")
    written.save(tmp_path / "checkpoint.npz")

    assert VectorCheckpoint.from_path(
        tmp_path / "checkpoint.npz"
    ).slots == written.slots
    assert bytes not in get_safe_globals()


def test_a_vector_checkpoint_reads_back_as_written(tmp_path: Path):
    """
    Asserts that a checkpoint of PQN or PPO reads back with the agent's side
    and each environment's slot as written, under the `weights_only=True`
    that `torch.load` reads its plain values through.
    """
    written = vector_checkpoint(2, 16)
    written.save(tmp_path / "checkpoint.npz")
    read = VectorCheckpoint.from_path(tmp_path / "checkpoint.npz")

    assert read.model_dump(exclude={"online"}) == written.model_dump(exclude={"online"})
    assert read.online["weight"].tolist() == [1.0, 2.0]


def vector_checkpoint(
    episodes : int,
    step     : int,
    presses  : bytes = bytes([1, 4, 4])
) -> VectorCheckpoint:
    """
    Builds the checkpoint of a run of PQN or PPO at `step` after `episodes`
    episodes, one environment `presses` into its next, by default three.
    """
    return VectorCheckpoint(
        episodes  = episodes,
        generator = {"bit_generator": "PCG64", "state": {"inc": 1, "state": 2**100}},
        moments   = Moments(count=8.0001, mean=0.25, var=2.0),
        online    = {"weight": tensor([1.0, 2.0])},
        optimizer = {"param_groups": [{"lr": 1e-4, "params": [0]}], "state": {}},
        slots     = [
            Slot(
                count     = 1,
                generator = {
                    "bit_generator" : "PCG64",
                    "state"         : {"inc": 3, "state": 2**70}
                },
                recording = Recording(presses=presses, timer_div=9),
                returned  = -0.5,
                totals    = [1.0, 2.0]
            )
        ],
        step = step
    )
