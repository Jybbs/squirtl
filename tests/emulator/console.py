"""
Pins how `GameBoy` runs a cartridge through PyBoy, covering:

- The arguments a boot hands PyBoy, the SDL2 window it opens, and the save
  beside the cartridge that a boot never reads and a close never writes
- Each press, its one tick, and the gray frame read after it, beside the
  RGB screen, each a copy, and a press refused for holding its button past
  its frames
- The byte each symbol reads, the digest of the state a reset leaves, the
  stop a close makes, the intro a start plays, and the state and DIV a
  reset returns to
- The state a load returns to, the frame it last rendered included, and the
  DIV a write sets, leaving the rest of the state as it was
"""

from collections.abc import Callable, Iterator
from common.console  import StandIn
from functools       import partial
from itertools       import batched
from numpy           import arange, ndarray, shares_memory, tile, uint8
from numpy.random    import default_rng
from numpy.testing   import assert_array_equal
from operator        import attrgetter
from pyboy.utils     import PyBoyInvalidOperationException
from pytest          import MonkeyPatch, fixture, mark, param, raises
from random          import getstate

from squirtl.emulator         import console
from squirtl.emulator.console import GameBoy
from squirtl.emulator.schemas import Button, Cartridge, EmulatorSettings, Symbol

type Boot = Callable[[EmulatorSettings], GameBoy]


@fixture
def boot(cartridge: Cartridge, monkeypatch: MonkeyPatch) -> Boot:
    """
    Builds a function that boots `cartridge` under the settings it is
    given, on `StandIn` in place of `PyBoy`, so a test reads back each call
    `GameBoy` makes on it.
    """
    monkeypatch.setattr(console, "PyBoy", StandIn)

    return partial(GameBoy.boot, cartridge)


@fixture
def game_boy(cartridge: Cartridge) -> Iterator[GameBoy]:
    """
    Boots `cartridge` on PyBoy under the default settings and closes it once
    the test ends.
    """
    with GameBoy.boot(cartridge, EmulatorSettings()) as booted:
        yield booted


@mark.parametrize(
    ("open_window", "window"),
    [param(False, "null", id="headless"), param(True, "SDL2", id="a-window")]
)
def test_a_boot_runs_silent_and_headless_unless_a_window_opens(
    boot        : Boot,
    open_window : bool,
    window      : str
):
    """
    Asserts that a boot hands PyBoy its sound off, its log level at `ERROR`,
    and the null window, which draws nothing, unless `open_window` opens an
    SDL2 window.
    """
    assert boot(EmulatorSettings(open_window=open_window)).emulator.options == {
        "log_level"      : "ERROR",
        "sound_emulated" : False,
        "window"         : window
    }


def test_a_boot_hands_pyboy_the_cartridge_as_bytes(boot: Boot, cartridge: Cartridge):
    """
    Asserts that a boot hands PyBoy a stream of the cartridge's bytes rather
    than its path, so PyBoy derives no path to a file beside it.
    """
    assert boot(EmulatorSettings()).emulator.gamerom.getvalue() == cartridge.data


def test_a_boot_reads_no_save_beside_the_cartridge(game_boy: GameBoy):
    """
    Asserts that the first byte of the cartridge's RAM reads zero although
    `rom.gb.ram` beside the cartridge holds `0xAB` in every byte, which
    PyBoy loads into that RAM when it boots from the cartridge's path.
    """
    assert game_boy.emulator.memory[0, 0xA000] == 0


def test_a_close_writes_nothing_beside_the_cartridge(cartridge: Cartridge):
    """
    Asserts that a console whose cartridge RAM changed leaves the directory
    of its cartridge holding the files it held, each byte for byte, where
    PyBoy's default `stop()` writes that RAM to a save beside a cartridge
    booted from its path.
    """
    held = {path: path.read_bytes() for path in cartridge.path.parent.iterdir()}

    with GameBoy.boot(cartridge, EmulatorSettings()) as game_boy:
        game_boy.emulator.memory[0, 0xA000] = 0x01

    assert {path: path.read_bytes() for path in cartridge.path.parent.iterdir()} == held


def test_a_closed_console_runs_no_further_frame(cartridge: Cartridge):
    """
    Asserts that leaving a `with` block stops the emulator, so a later
    tick raises, where PyBoy's default `stop()` fails to save the RAM of a
    cartridge handed over as bytes and leaves the emulator running.
    """
    with GameBoy.boot(cartridge, EmulatorSettings()) as game_boy:
        pass

    with raises(PyBoyInvalidOperationException, match="stopped"):
        game_boy.emulator.tick(1)


@mark.parametrize(
    ("button", "pressed"),
    [
        param(None, [], id="no-press"),
        *(param(button, [("button", button, 3)], id=button) for button in Button)
    ]
)
def test_a_press_sends_any_button_then_ticks_before_reading_the_screen(
    boot    : Boot,
    button  : Button | None,
    pressed : list[tuple[str, Button, int]]
):
    """
    Asserts that a press hands PyBoy the name of its button, where it has
    one, held for the `hold` its settings name, then advances every frame
    the step names in one tick, and reads the screen only after that tick,
    so the frame it returns is the one that tick rendered.
    """
    game_boy = boot(EmulatorSettings(hold=3))
    game_boy.press(button, 24)

    assert game_boy.emulator.calls == [*pressed, ("tick", 24), ("screen",)]


def test_a_div_write_sets_div_alone(game_boy: GameBoy):
    """
    Asserts that a DIV write on PyBoy after a reset at 0 leaves 77 in the
    register at `0xFF04`, which a write to that address would clear, and the
    console in the state a reset at 77 leaves.
    """
    game_boy.start()
    reached = []

    for writes in ([game_boy.reset, 77], [game_boy.reset, 0, game_boy.set_div, 77]):
        for write, timer_div in batched(writes, 2):
            write(timer_div)

        reached.append((game_boy.emulator.memory[0xFF04], game_boy.digest))

    assert reached == [(77, reached[0][1])] * 2


def test_a_load_returns_to_the_state_saved_and_the_frame_it_rendered(game_boy: GameBoy):
    """
    Asserts that loading a state the console saved undoes the frames and the
    write to the game's memory taken since, leaving the same state and the
    same gray frame.
    """
    game_boy.start()
    game_boy.press(None, 120)
    state, frame = game_boy.state, game_boy.grayscale
    game_boy.emulator.memory[Symbol.W_CUR_MAP] = 9
    game_boy.press(None, 30)
    game_boy.load(state)

    assert game_boy.read(Symbol.W_CUR_MAP) == 0
    assert game_boy.state == state
    assert_array_equal(game_boy.grayscale, frame, strict=True)


def test_a_press_holding_its_button_past_its_frames_is_refused(boot: Boot):
    """
    Asserts that a press advancing fewer frames than its settings hold the
    button for raises before PyBoy receives the button, rather than leaving
    it held into the next tick.
    """
    game_boy = boot(EmulatorSettings(hold=3))

    with raises(ValueError, match="holds its button for 3 frames, more than the 2"):
        game_boy.press(Button.A, 2)

    assert game_boy.emulator.calls == []


def test_a_read_past_a_symbol_reads_the_byte_at_its_offset(game_boy: GameBoy):
    """
    Asserts that reading `offset` bytes past a symbol returns the byte at
    that index of the array the symbol starts, where the symbol's own byte
    holds another value.
    """
    game_boy.emulator.memory[Symbol.W_EVENT_FLAGS]     = 0x01
    game_boy.emulator.memory[Symbol.W_EVENT_FLAGS + 4] = 0x5A

    assert game_boy.read(Symbol.W_EVENT_FLAGS, 4) == 0x5A


@mark.parametrize(
    ("hp", "fainted"),
    [
        param([], False, id="no-party"),
        param([0, 0], True, id="every-one-fainted"),
        param([0, 1], False, id="low-byte-left"),
        param([0, 256], False, id="high-byte-left")
    ]
)
def test_a_party_faints_once_every_pokemon_holds_no_hp(
    fainted  : bool,
    game_boy : GameBoy,
    hp       : list[int]
):
    """
    Asserts that a party faints where it holds a Pokémon and every one's
    two bytes of HP, read $2C bytes apart, are zero, and that a party of
    none stands.
    """
    memory = game_boy.emulator.memory

    memory[Symbol.W_PARTY_COUNT] = len(hp)

    for mon, points in enumerate(hp):
        address = Symbol.W_PARTY_MONS + 1 + 0x2C * mon

        memory[address : address + 2] = points.to_bytes(2)

    assert game_boy.fainted is fainted


@mark.parametrize(
    ("hp", "fighting", "species", "points", "number", "fainted"),
    [
        param([3], 1, 0xB0, 0, 0, True, id="knocked-out-in-battle"),
        param([19], 1, 0x00, 0, 0, False, id="battle-intro"),
        param([21], 0, 0xB0, 0, 0, False, id="after-a-battle"),
        param([0], 1, 0xB0, 1, 0, False, id="low-byte-left"),
        param([0], 1, 0xB0, 256, 0, False, id="high-byte-left"),
        param([3, 10], 1, 0xB0, 0, 0, False, id="one-left-in-the-party"),
        param([0, 10], 1, 0xB0, 0, 1, True, id="second-knocked-out")
    ]
)
def test_a_party_in_battle_faints_once_the_pokemon_sent_out_faints(
    fainted  : bool,
    fighting : int,
    game_boy : GameBoy,
    hp       : list[int],
    number   : int,
    points   : int,
    species  : int
):
    """
    Asserts that, in a battle whose Pokémon `LoadBattleMonFromParty`
    has written, the Pokémon `wPlayerMonNumber` names reads its HP from
    `wBattleMon` rather than from its party struct, so a party faints at
    the faint itself, whereas a battle's intro, its species zero over the
    last battle's HP, and the map after a battle read the party. `fighting`
    is `wIsInBattle`, and `species` and `points` are the species and the HP
    `wBattleMon` holds.
    """
    memory = game_boy.emulator.memory

    memory[Symbol.W_IS_IN_BATTLE]      = fighting
    memory[Symbol.W_BATTLE_MON]        = species
    memory[Symbol.W_PLAYER_MON_NUMBER] = number
    memory[Symbol.W_PARTY_COUNT]       = len(hp)

    memory[Symbol.W_BATTLE_MON + 1 : Symbol.W_BATTLE_MON + 3] = points.to_bytes(2)

    for mon, left in enumerate(hp):
        address = Symbol.W_PARTY_MONS + 1 + 0x2C * mon

        memory[address : address + 2] = left.to_bytes(2)

    assert game_boy.fainted is fainted


def test_a_reset_at_one_timer_div_leaves_a_state_of_one_digest(game_boy: GameBoy):
    """
    Asserts that a reset at one `timer_div` leaves the console in a state of
    one digest, whatever the game's memory took since, that a write to the
    memory changes the digest, and that another `timer_div` leaves another.
    """
    game_boy.start()
    game_boy.reset(42)
    first = game_boy.digest
    game_boy.emulator.memory[Symbol.W_CUR_MAP] = 9
    written = game_boy.digest
    game_boy.reset(42)
    again = game_boy.digest
    game_boy.reset(43)

    assert (written != first, again, game_boy.digest != first) == (True, first, True)


@mark.parametrize("button", Button, ids=attrgetter("name"))
def test_each_button_names_one_pyboy_presses(button: Button, game_boy: GameBoy):
    """
    Asserts that PyBoy takes the value of each button as the name of a
    button it presses, where it raises `PyBoyInvalidInputException` on a
    name it does not know, held for exactly the frames the press advances.
    """
    game_boy.press(button, game_boy.settings.hold)


@mark.parametrize("symbol", Symbol, ids=attrgetter("name"))
def test_each_symbol_reads_the_byte_at_its_address(game_boy: GameBoy, symbol: Symbol):
    """
    Asserts that reading a symbol returns the byte written at the address
    its member holds.
    """
    game_boy.emulator.memory[symbol] = 0x5A

    assert game_boy.read(symbol) == 0x5A


def test_a_start_leaves_pythons_global_generator_undrawn(game_boy: GameBoy):
    """
    Asserts that a start on PyBoy leaves the state of Python's global
    generator as it found it.
    """
    before, _, after = getstate(), game_boy.start(), getstate()

    assert after == before


def test_a_start_plays_the_intro_through_the_game_wrapper(boot: Boot):
    """
    Asserts that a start hands PyBoy's game wrapper a `timer_div` of 0 in
    place of the `None` that draws one from Python's global generator.
    """
    game_boy = boot(EmulatorSettings())
    game_boy.start()

    assert game_boy.emulator.calls == [("start_game", 0)]


def test_a_window_the_setting_opens_is_one_pyboy_runs(
    cartridge   : Cartridge,
    monkeypatch : MonkeyPatch
):
    """
    Asserts that PyBoy boots and advances a frame in the window
    `open_window` names, under SDL's `dummy` video driver, which draws on
    no display.
    """
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")

    with GameBoy.boot(cartridge, EmulatorSettings(open_window=True)) as game_boy:
        assert game_boy.emulator.tick(1)


def test_the_frame_a_press_returns_holds_the_red_channel_alone(boot: Boot):
    """
    Asserts that the frame a press returns is a `(144, 160)` array of
    `uint8` holding the red channel of PyBoy's RGBA frame alone, read from a
    stand-in frame of bytes a generator seeded at 0 draws, whose red channel
    no reduction across the channels gives.
    """
    game_boy                = boot(EmulatorSettings())
    game_boy.emulator.frame = default_rng(0).integers(
        256,
        dtype = uint8,
        size  = (144, 160, 4)
    )

    assert_array_equal(
        game_boy.press(None, 1),
        game_boy.emulator.frame[..., 0],
        strict = True
    )


@mark.parametrize(
    "read",
    [
        param(lambda game_boy: game_boy.press(None, 1), id="the-frame-a-press-returns"),
        param(attrgetter("screen"),                     id="the-screen")
    ]
)
def test_each_frame_read_is_a_copy(
    game_boy : GameBoy,
    read     : Callable[[GameBoy], ndarray]
):
    """
    Asserts that the gray frame a press returns and the RGB screen each
    share no memory with the frame PyBoy overwrites at each rendered frame.
    """
    assert not shares_memory(read(game_boy), game_boy.emulator.screen.ndarray)


@mark.parametrize(
    "timer_div",
    [param(0, id="zero"), param(255, id="the-top-of-8-bits")]
)
def test_a_reset_returns_to_the_start_with_its_timer_div_in_div(
    game_boy  : GameBoy,
    timer_div : int
):
    """
    Asserts that a reset on PyBoy undoes a write the game's memory took
    after the start and leaves `timer_div` in the DIV register at `0xFF04`.
    """
    game_boy.start()
    game_boy.emulator.memory[Symbol.W_CUR_MAP] = 9
    game_boy.press(None, 3)
    game_boy.reset(timer_div)

    assert (game_boy.read(Symbol.W_CUR_MAP), game_boy.emulator.memory[0xFF04]) == (
        0, timer_div
    )


def test_the_screen_holds_the_rgb_channels_alone(boot: Boot):
    """
    Asserts that the screen is a `(144, 160, 3)` array of `uint8` holding
    the red, green, and blue channels of PyBoy's RGBA frame in that order,
    read from a stand-in frame whose every pixel holds each channel's index
    in that channel.
    """
    assert_array_equal(
        boot(EmulatorSettings()).screen,
        tile(arange(3, dtype=uint8), (144, 160, 1)),
        strict = True
    )


def test_the_tiles_are_the_screen_of_tiles_wtilemap_holds(game_boy: GameBoy):
    """
    Asserts that the tiles hold the 20 by 18 bytes from `wTileMap` on, the
    last of them included and the byte past them left out.
    """
    memory = game_boy.emulator.memory

    memory[Symbol.W_TILE_MAP + 359] = 0x5A
    memory[Symbol.W_TILE_MAP + 360] = 0x5B

    assert (len(game_boy.tiles), game_boy.tiles[-1]) == (360, 0x5A)
