"""
Pins the worker each rollout runs in, covering:

- The process a worker boots, which leads a process group of its own,
  exits printing nothing, and ends once its parent has ended, and the
  modules it imports, none of them PyTorch
- A rollout dead where it ends on the `wTileMap` and the position it started
  from, whatever its screen shows, or blacks out outside Oak's lab, at the
  faint in a battle, and surviving where either changes or it earns reward
- A rollout stopping at the press that sets a flag, playing on past each
  new square, or playing on where it brings back a node
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
from os         import getpgrp, getpid, kill
from pickle     import dumps
from pytest     import CaptureFixture, MonkeyPatch, approx, mark, param
from subprocess import PIPE, Popen, check_output
from sys        import executable
from time       import monotonic, sleep
from types      import SimpleNamespace

from squirtl.emulator.console    import GameBoy
from squirtl.emulator.schemas    import Symbol
from squirtl.environment.schemas import Entry, Snapshot
from squirtl.reward.schemas      import Event
from squirtl.search              import workers
from squirtl.search.schemas      import Ending, SearchRollout
from squirtl.search.workers      import boot, roll


def alive(pid: int) -> bool:
    """
    Reads whether a process with `pid` still exists, through the null
    signal, which checks the process without signaling it.
    """
    try:
        kill(pid, 0)
    except ProcessLookupError:
        return False

    return True


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


def test_a_boot_moves_into_a_group_of_its_own_and_makes_the_environment(
    monkeypatch   : MonkeyPatch,
    specification : EnvSpec
):
    """
    Asserts that a boot moves its process into a process group of its own,
    which a signal to the main process's group then leaves out, starts
    a daemon thread ending the process with its parent, and makes the
    environment that `specification` names, closing it as the process exits.
    """
    moved, closing, started = [], [], []
    monkeypatch.setattr(workers, "register", closing.append)
    monkeypatch.setattr(workers, "setpgrp", lambda: moved.append(True))
    monkeypatch.setattr(
        workers,
        "Thread",
        lambda **thread: SimpleNamespace(start=lambda: started.append(thread))
    )

    boot(specification)

    with workers.environment as environment:
        assert (moved, environment.spec.id) == ([True], specification.id)
        assert closing == [environment.close]
        assert started == [{"daemon": True, "target": workers.exit_with_parent}]


def test_a_spawned_worker_ends_once_its_parent_is_killed(specification: EnvSpec):
    """
    Asserts that a spawned worker, which no signal to its parent's process
    group reaches, ends within seconds of a `SIGKILL` to the process whose
    pool started it.
    """
    script = "\n".join(
        [
            "import pickle, sys, time",
            "from concurrent.futures import ProcessPoolExecutor",
            "from multiprocessing import get_context",
            "from os import getpid",
            "from squirtl.search.workers import boot",
            "spec = pickle.load(sys.stdin.buffer)",
            "pool = ProcessPoolExecutor(1, get_context('spawn'), boot, (spec,))",
            "print(pool.submit(getpid).result(), flush=True)",
            "time.sleep(60)"
        ]
    )

    with Popen([executable, "-c", script], stdin=PIPE, stdout=PIPE) as parent:
        parent.stdin.write(dumps(specification))
        parent.stdin.close()
        worker = int(parent.stdout.readline())
        parent.kill()

    deadline = monotonic() + 10

    while alive(worker) and monotonic() < deadline:
        sleep(0.1)

    assert not alive(worker)


def test_a_spawned_worker_exits_printing_nothing(
    capfd         : CaptureFixture[str],
    specification : EnvSpec
):
    """
    Asserts that spawned workers booting the environment print nothing to
    the standard error they share with the main process as the pool shuts
    them down, the emulator stopping before the interpreter tears down.
    """
    capfd.readouterr()

    with ProcessPoolExecutor(
        initargs    = (specification,),
        initializer = boot,
        max_workers = 2,
        mp_context  = get_context("spawn")
    ) as pool:
        [*pool.map(abs, range(2))]

    assert "excepthook" not in capfd.readouterr().err


def test_a_spawned_worker_leads_a_process_group_apart_from_the_main_process(
    specification: EnvSpec
):
    """
    Asserts that a spawned worker leads a process group of its own, apart
    from the group of the process that started it.
    """
    with ProcessPoolExecutor(
        initargs    = (specification,),
        initializer = boot,
        max_workers = 1,
        mp_context  = get_context("spawn")
    ) as pool:
        worker, group = (pool.submit(call).result() for call in (getpid, getpgrp))

    assert (group, group == getpgrp()) == (worker, False)


def test_a_worker_ends_at_once_after_its_parent_has_ended(monkeypatch: MonkeyPatch):
    """
    Asserts that the thread a boot starts waits for the process that started
    the worker to end, then ends the worker with status 1.
    """
    calls = []
    monkeypatch.setattr(
        workers,
        "parent_process",
        lambda: SimpleNamespace(join=lambda: calls.append("joined"))
    )
    monkeypatch.setattr(workers, "_exit", calls.append)

    workers.exit_with_parent()

    assert calls == ["joined", 1]


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
def test_a_rollout_changing_the_tile_map_in_place_is_alive(
    monkeypatch : MonkeyPatch,
    playing     : Callable[..., Ending]
):
    """
    Asserts that a rollout leaving the player on the square it started on
    survives where `wTileMap` has changed, as advancing dialogue changes it.
    """
    def draw(game_boy: GameBoy):
        """
        Changes the first tile `wTileMap` holds.
        """
        game_boy.emulator.memory[Symbol.W_TILE_MAP] ^= 0xFF

    pressing_after(draw, monkeypatch)

    assert not playing(b"\x00").dead


@mark.usefixtures("booted")
def test_a_rollout_changing_the_screen_alone_in_place_is_dead(
    monkeypatch : MonkeyPatch,
    playing     : Callable[..., Ending]
):
    """
    Asserts that a rollout leaving the player on the square and the tile
    map it started on ends dead where only the screen has changed, as Blue
    turning in place changes his sprite alone, which the press here stands
    in for by inverting the palette at `0xFF47`.
    """
    def invert(game_boy: GameBoy):
        """
        Inverts the palette.
        """
        game_boy.emulator.memory[0xFF47] ^= 0xFF

    pressing_after(invert, monkeypatch)

    assert playing(b"\x00").dead


@mark.parametrize(
    ("map", "battle", "dead"),
    [
        param(0x00, False, True, id="pallet-town"),
        param(0x28, False, False, id="oaks-lab"),
        param(0x0C, True, True, id="knocked-out-on-route-1"),
        param(0x28, True, False, id="knocked-out-in-oaks-lab")
    ]
)
@mark.usefixtures("booted", "game")
def test_a_rollout_whose_party_faints_blacks_out_outside_oaks_lab(
    battle      : bool,
    dead        : bool,
    map         : int,
    monkeypatch : MonkeyPatch,
    playing     : Callable[..., Ending]
):
    """
    Asserts that a rollout moving the player ends dead on the press its one
    Pokémon faints on, stopping there, where the map is any but Oak's lab,
    in which the game lets Blue lose to the rival, and plays on alive there.
    In a battle, the faint is a battle HP of zero beside a party struct
    still holding the HP of the turn before.
    """
    def faint(game_boy: GameBoy):
        """
        Puts the player on `map` with one Pokémon holding no HP, in a battle
        where `battle` holds.
        """
        memory = game_boy.emulator.memory

        memory[Symbol.W_CUR_MAP]        = map
        memory[Symbol.W_PARTY_COUNT]    = 1
        memory[Symbol.W_IS_IN_BATTLE]   = battle
        memory[Symbol.W_BATTLE_MON]     = 0xB0 if battle else 0x00
        memory[Symbol.W_PARTY_MONS + 2] = 3 if battle else 0

    pressing_after(faint, monkeypatch)

    ended = playing(b"\x01\x01\x01")

    assert (ended.dead, len(ended.presses)) == (dead, 1 if dead else 3)


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
def test_a_rollout_stops_at_the_press_setting_a_flag(playing: Callable[..., Ending]):
    """
    Asserts that a rollout of the button moving six squares a press plays on
    past the new squares its first two presses reach and stops on its third,
    which reaches square 18 and the first milestone, the reward it reports
    paying that flag and the three new squares.
    """
    ended = playing(b"\x06" * 8)

    assert (ended.presses, ended.reward) == (b"\x06" * 3, approx(0.1 + 3 * 0.00025))


@mark.usefixtures("booted", "game")
def test_a_rollout_that_does_not_halt_plays_every_press(playing: Callable[..., Ending]):
    """
    Asserts that a rollout bringing back a node plays every press past the
    one setting a flag, the reward it reports paying the flag and each of
    the eight new squares.
    """
    ended = playing(b"\x06" * 8, halting=False)

    assert (ended.presses, ended.reward) == (b"\x06" * 8, approx(0.1 + 8 * 0.00025))


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
    rollouts = [SearchRollout(presses=bytes([n % 7]) * 3, snapshot=root) for n in range(
        6
    )]

    with ProcessPoolExecutor(
        initargs    = (specification,),
        initializer = boot,
        max_workers = processes,
        mp_context  = get_context("spawn")
    ) as pool:
        endings = [*pool.map(roll, rollouts)]

    assert endings == [roll(rollout) for rollout in rollouts]
