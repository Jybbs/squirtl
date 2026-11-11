"""
Pins the worker each rollout runs in, covering:

- The process a worker boots, which ignores a terminal's interrupt, and the
  modules it imports, none of them PyTorch
- A rollout dead where it ends on the screen and the position it started
  from, and surviving where either changes or it earns reward
- A rollout stopping at the press that earns reward, or playing on where it
  brings back a node
- What an ending holds, each newest frame and each press
- One rollout reaching one ending, whichever rollout ran before it
- A real pool returning each ending in the order submitted, on every worker
  count
"""

from collections.abc    import Callable
from common.console     import set_event
from concurrent.futures import ProcessPoolExecutor
from gymnasium          import Env
from gymnasium.envs.registration import EnvSpec
from multiprocessing             import get_context
from numpy      import frombuffer, uint8
from pytest     import MonkeyPatch, mark, param
from signal     import SIGINT, SIG_IGN, getsignal, signal
from subprocess import check_output
from sys        import executable

from squirtl.emulator.console    import GameBoy
from squirtl.environment.schemas import Entry, Snapshot
from squirtl.reward.schemas      import Event
from squirtl.search              import workers
from squirtl.search.schemas      import Ending, Rollout
from squirtl.search.workers      import boot, roll


def pressing_after(effect: Callable[[GameBoy], object], monkeypatch: MonkeyPatch):
    """
    Makes each press of a `GameBoy` run `effect` on it first.
    """
    press = GameBoy.press

    def pressing(game_boy: GameBoy, *held: object) -> object:
        """
        Runs `effect`, then presses as `GameBoy.press` does.
        """
        effect(game_boy)

        return press(game_boy, *held)

    monkeypatch.setattr(GameBoy, "press", pressing)


def test_a_boot_ignores_the_interrupt_and_makes_the_environment(specification: EnvSpec):
    """
    Asserts that a boot ignores the interrupt a terminal sends its whole
    foreground group, and makes the environment that `specification` names.
    """
    handler = getsignal(SIGINT)

    boot(specification)

    try:
        with workers.environment as environment:
            assert (
                getsignal(SIGINT),
                environment.spec.id
            ) == (SIG_IGN, specification.id)
    finally:
        signal(SIGINT, handler)


def test_a_worker_imports_no_pytorch():
    """
    Asserts that importing the worker's module in a fresh interpreter
    imports no module of PyTorch, since a worker runs none of it.
    """
    modules = check_output(
        [executable, "-c", "import sys, squirtl.search.workers; print(*sys.modules)"],
        text = True
    ).split()

    assert "torch" not in modules


@mark.usefixtures("booted", "game")
def test_a_rollout_ending_where_it_started_is_dead(playing: Callable[..., Ending]):
    """
    Asserts that a rollout of no press at all, on a cartridge whose screen
    never changes, ends dead.
    """
    assert playing(b"\x00\x00\x00").dead


@mark.usefixtures("booted", "game")
def test_a_rollout_moving_the_player_on_one_screen_is_alive(
    playing: Callable[..., Ending]
):
    """
    Asserts that a rollout that moves the player survives on a screen that
    never changes.
    """
    assert not playing(b"\x01\x00").dead


@mark.usefixtures("booted")
def test_a_rollout_changing_the_screen_in_place_is_alive(
    monkeypatch : MonkeyPatch,
    playing     : Callable[..., Ending]
):
    """
    Asserts that a rollout leaving the player on the square it started on
    survives where the screen has changed, as advancing dialogue does, which
    the press here does by inverting the palette at `0xFF47`.
    """
    def invert(game_boy: GameBoy):
        """
        Inverts the palette.
        """
        game_boy.emulator.memory[0xFF47] ^= 0xFF

    pressing_after(invert, monkeypatch)

    assert not playing(b"\x00").dead


@mark.usefixtures("booted")
def test_a_rollout_earning_reward_in_place_is_alive(
    monkeypatch : MonkeyPatch,
    playing     : Callable[..., Ending]
):
    """
    Asserts that a rollout setting a flag with the screen and the position
    as they were survives, so the reward it earned reaches the group.
    """
    pressing_after(
        effect = lambda game_boy: set_event(
            Event.EVENT_OAK_APPEARED_IN_PALLET,
            game_boy.emulator.memory
        ),
        monkeypatch = monkeypatch
    )

    ended = playing(b"\x00\x00")

    assert (ended.dead, ended.reward > 0.0) == (False, True)


@mark.usefixtures("booted", "game")
def test_a_rollout_stops_at_the_press_earning_reward(playing: Callable[..., Ending]):
    """
    Asserts that a rollout of the button moving six squares a press stops
    on its third press, which reaches square 18 and the first milestone, the
    reward it reports paying that flag alone.
    """
    ended = playing(b"\x06" * 8)

    assert (ended.presses, ended.reward) == (b"\x06" * 3, 0.1)


@mark.usefixtures("booted", "game")
def test_a_rollout_that_does_not_halt_plays_every_press(playing: Callable[..., Ending]):
    """
    Asserts that a rollout bringing back a node plays every press past the
    one earning reward.
    """
    ended = playing(b"\x06" * 8, halting=False)

    assert (ended.presses, ended.reward) == (b"\x06" * 8, 0.1)


@mark.usefixtures("booted", "game")
def test_a_rollout_stops_at_the_starter(playing: Callable[..., Ending]):
    """
    Asserts that a rollout from square 18 reaches the starter on the eighth
    press, at six squares a press, and ends there on a snapshot whose tally
    holds the flag.
    """
    ended = playing(b"\x06" * 16, snapshot=playing(b"\x06" * 3).snapshot)

    assert ended.presses == b"\x06" * 8
    assert Event.EVENT_GOT_STARTER in ended.snapshot.tally.events


@mark.usefixtures("booted", "game")
def test_an_ending_holds_each_press_and_its_newest_frame(
    booted  : Env,
    playing : Callable[..., Ending]
):
    """
    Asserts that an ending holds the presses it took beside one frame of
    the environment's shape per press, the last of them the newest frame the
    stack of its end holds.
    """
    ended = playing(b"\x01\x02\x03")

    assert ended.presses == b"\x01\x02\x03"
    assert booted.observation_space[Entry.FRAMES].shape == (4, 72, 80)
    assert (
        frombuffer(ended.frames, uint8).reshape(3, 72, 80)[-1]
        == booted.reset(options={"snapshot": ended.snapshot})[0][Entry.FRAMES][-1]
    ).all()


@mark.usefixtures("booted", "game")
def test_one_rollout_reaches_one_ending_whichever_rollout_ran_before_it(
    playing: Callable[..., Ending]
):
    """
    Asserts that a rollout reaches the same ending byte for byte before and
    after another played, since each restores all it depends on.
    """
    endings = [
        playing(b"\x03\x04\x05"),
        playing(b"\x06" * 16, halting=False),
        playing(b"\x03\x04\x05")
    ]

    assert endings[0] == endings[2]


@mark.usefixtures("booted", "game")
def test_a_rollout_from_a_rollouts_end_matches_one_played_straight_through(
    playing: Callable[..., Ending]
):
    """
    Asserts that playing part of a list of presses, then the rest from the
    snapshot it ended on, reaches the state and the stack that playing them
    all reaches.
    """
    whole = playing(b"\x01\x02\x03\x04\x05")
    part  = playing(b"\x01\x02", halting=False)
    rest  = playing(b"\x03\x04\x05", snapshot=part.snapshot)

    assert rest.snapshot == whole.snapshot
    assert part.frames + rest.frames == whole.frames


@mark.parametrize("processes", [param(1, id="one"), param(2, id="two")])
def test_a_pool_returns_each_ending_in_the_order_submitted(
    processes     : int,
    root          : Snapshot,
    specification : EnvSpec
):
    """
    Asserts that spawned workers return the ending of each rollout in
    the order the rollouts were submitted, each equal to the one the same
    rollout reaches in the process running the test, whatever the worker
    count.
    """
    rollouts = [Rollout(presses=bytes([n % 7]) * 3, snapshot=root) for n in range(6)]

    with ProcessPoolExecutor(
        initargs    = (specification,),
        initializer = boot,
        max_workers = processes,
        mp_context  = get_context("spawn")
    ) as pool:
        endings = [*pool.map(roll, rollouts)]

    assert endings == [roll(rollout) for rollout in rollouts]
