"""
Pins how `GameBoy` runs a cartridge through PyBoy, covering:

- The arguments a boot hands PyBoy under each setting of the window, and
  the SDL2 window PyBoy opens under SDL's dummy video driver
- The save beside the cartridge, which a boot never reads and a close
  never writes
- The press of any button and the one tick of the frames a step names
- The screen a press returns, an RGB copy no later frame overwrites
- The byte each symbol reads, the state a capture saves and a restore loads,
  and the stop a close makes
"""

from collections.abc import Callable, Iterator
from common.console  import StandIn
from functools       import partial
from numpy           import arange, shares_memory, tile, uint8
from numpy.testing   import assert_array_equal
from operator        import attrgetter
from pyboy.utils     import PyBoyInvalidOperationException
from pytest          import MonkeyPatch, fixture, mark, param, raises

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
        *(param(button, [("button", button)], id=button) for button in Button)
    ]
)
def test_a_press_sends_any_button_then_one_tick_of_its_frames(
    boot    : Boot,
    button  : Button | None,
    pressed : list[tuple[str, Button]]
):
    """
    Asserts that a press hands PyBoy the name of its button, where it has
    one, and then advances every frame the step names in one tick.
    """
    game_boy = boot(EmulatorSettings())
    game_boy.press(button, 24)

    assert game_boy.emulator.calls == [*pressed, ("tick", 24)]


def test_a_restore_returns_the_console_to_its_capture(game_boy: GameBoy):
    """
    Asserts that restoring a state captured in memory returns the whole
    console to it, undoing a write the game's memory took after the capture.
    """
    state = game_boy.capture()
    game_boy.emulator.memory[Symbol.W_CUR_MAP] = 9
    game_boy.restore(state)

    assert game_boy.capture() == state


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


@mark.parametrize("button", Button, ids=attrgetter("name"))
def test_each_button_names_one_pyboy_presses(button: Button, game_boy: GameBoy):
    """
    Asserts that PyBoy takes the value of each button as the name of a
    button it presses, where it raises `PyBoyInvalidInputException` on a
    name it does not know.
    """
    game_boy.press(button, 1)


@mark.parametrize("symbol", Symbol, ids=attrgetter("name"))
def test_each_symbol_reads_the_byte_at_its_address(game_boy: GameBoy, symbol: Symbol):
    """
    Asserts that reading a symbol returns the byte written at the address
    its member holds.
    """
    game_boy.emulator.memory[symbol] = 0x5A

    assert game_boy.read(symbol) == 0x5A


def test_the_screen_a_press_returns_holds_the_rgb_channels_alone(boot: Boot):
    """
    Asserts that the screen a press returns is a `(144, 160, 3)` array of
    `uint8` holding the red, green, and blue channels of PyBoy's RGBA frame
    in that order, read from a stand-in frame whose every pixel holds each
    channel's index in that channel.
    """
    assert_array_equal(
        boot(EmulatorSettings()).press(None, 1),
        tile(arange(3, dtype=uint8), (144, 160, 1)),
        strict = True
    )


def test_the_screen_a_press_returns_is_a_copy(game_boy: GameBoy):
    """
    Asserts that the screen a press returns shares no memory with the frame
    PyBoy overwrites at each rendered frame.
    """
    assert not shares_memory(game_boy.press(None, 1), game_boy.emulator.screen.ndarray)
