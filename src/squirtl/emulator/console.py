"""
Defines `GameBoy`, which runs a verified cartridge through PyBoy, beside the
protocols naming the members of PyBoy that `GameBoy` calls:

- `Emulator`, the emulator itself
- `GameWrapper`, the wrapper PyBoy loads for the game the cartridge holds
- `Memory`, the view of the game's memory
- `Screen`, the screen object holding the frame PyBoy renders
"""

from contextlib  import AbstractContextManager
from dataclasses import dataclass, field
from io          import BytesIO
from numpy       import ndarray
from pyboy       import PyBoy
from typing      import BinaryIO, Protocol, Self

from squirtl.emulator.schemas import Button, Cartridge, EmulatorSettings, Symbol


class GameWrapper(Protocol):
    """
    The members of the game wrapper `PyBoy.game_wrapper` holds that
    `GameBoy` calls.
    """

    def reset_game(self, timer_div: int | None = None):
        """
        Loads the state `start_game` saved, then writes `timer_div` into the
        DIV register.
        """

    def start_game(self, timer_div: int | None = None):
        """
        Plays through the game's intro to its first playable state, saves
        that state, then writes `timer_div` into the DIV register.
        """


class Memory(Protocol):
    """
    The view of the game's memory that `PyBoy.memory` holds.
    """

    def __getitem__(self, address: int, /) -> int:
        """
        Reads the byte at `address`.
        """


class Screen(Protocol):
    """
    The screen object `PyBoy.screen` holds, whose `ndarray` carries the
    frame PyBoy last rendered.
    """

    ndarray: ndarray
    """
    The frame PyBoy last rendered, a `(144, 160, 4)` array of `uint8` RGBA
    values that each rendered frame overwrites.
    """


class Emulator(Protocol):
    """
    The members of `PyBoy` that `GameBoy` calls.
    """

    game_wrapper : GameWrapper
    memory       : Memory
    screen       : Screen

    def button(self, input: str, delay: int = 1):
        """
        Presses the button `input` names for the next `delay` frames.
        """

    def load_state(self, file_like_object: BinaryIO):
        """
        Restores the whole state of the emulator from `file_like_object`.
        """

    def save_state(self, file_like_object: BinaryIO):
        """
        Writes the whole state of the emulator into `file_like_object`.
        """

    def stop(self, save: bool):
        """
        Stops the emulator, writing the cartridge's battery RAM only where
        `save` is set.
        """

    def tick(self, count: int = 1, render: bool = True, sound: bool = True) -> bool:
        """
        Advances `count` frames, rendering the last only where `render` is
        set and sampling its sound only where `sound` is.
        """


@dataclass(frozen=True)
class GameBoy(AbstractContextManager):
    """
    The console running a verified cartridge through the emulator it
    composes, pressing at most one button a step and reading the game's
    memory.
    """

    emulator: Emulator
    """
    The emulator running the cartridge, `PyBoy` itself or a test's stand-in.
    """

    settings: EmulatorSettings = field(default_factory=EmulatorSettings)
    """
    The settings the console was booted with, whose `hold` each press takes.
    """

    def __exit__(self, *raised: object):
        """
        Closes the console on leaving a `with` block, whether or not the
        block raised.
        """
        self.close()

    @property
    def screen(self) -> ndarray:
        """
        Copies the frame the emulator last rendered without its alpha
        channel, which PyBoy holds at 255 in every pixel.

        Returns:
            A `(144, 160, 3)` array of `uint8` RGB values, which no later frame
            overwrites.
        """
        return self.emulator.screen.ndarray[..., :3].copy()

    @classmethod
    def boot(cls, cartridge: Cartridge, settings: EmulatorSettings) -> Self:
        """
        Starts PyBoy on the bytes of `cartridge`, with sound off and no
        window unless `settings` opens one.

        Handed bytes, PyBoy derives no path to a `.ram`, `.rtc`, or `.sym`
        file and reads none beside the cartridge. It logs errors alone,
        since at its default level it warns at every boot that Pillow is
        missing, once for the screen's `image` and once for each of its
        recording plugins.
        """
        return cls(
            PyBoy(
                BytesIO(cartridge.data),
                log_level      = "ERROR",
                sound_emulated = False,
                window         = settings.window
            ),
            settings
        )

    def capture(self) -> bytes:
        """
        Saves the whole state of the console in memory, which `restore`
        loads back.
        """
        with BytesIO() as state:
            self.emulator.save_state(state)

            return state.getvalue()

    def close(self):
        """
        Stops the emulator without saving, since PyBoy's default `stop()`
        writes the cartridge's battery RAM to a file beside the cartridge's
        path, and for a cartridge handed over as bytes, which has none, it
        prints the `TypeError` that building the path raises and leaves the
        emulator running.
        """
        self.emulator.stop(save=False)

    def press(self, button: Button | None, frames: int) -> ndarray:
        """
        Presses `button` for the first `hold` frames the settings name,
        or nothing where it is `None`, and advances `frames` frames in one
        tick, rendering only the last.

        Raises:
            ValueError: Where `button` is held for more frames than the
                        press advances, which would carry it into the next
                        tick.

        Returns:
            The screen that last frame shows, as `screen` copies it.
        """
        if button:
            if frames < self.settings.hold:
                raise ValueError(
                    f"a press holds its button for {self.settings.hold} frames, "
                    f"more than the {frames} it advances"
                )

            self.emulator.button(button, self.settings.hold)

        self.emulator.tick(frames)

        return self.screen

    def read(self, symbol: Symbol, offset: int = 0) -> int:
        """
        Reads the byte `offset` bytes past the address `symbol` names in
        the game's memory, so an offset into an array such as `wEventFlags`
        reads the byte at that index.
        """
        return self.emulator.memory[symbol + offset]

    def reset(self, timer_div: int):
        """
        Loads the state `start` saved and writes `timer_div` into the DIV
        register, the counter pret/pokered's `Random_` reads into the game's
        random numbers on every frame.
        """
        self.emulator.game_wrapper.reset_game(timer_div)

    def restore(self, state: bytes):
        """
        Loads a state `capture` saved, returning the console to that
        instant.
        """
        self.emulator.load_state(BytesIO(state))

    def start(self):
        """
        Plays through the game's intro to Red's bedroom, the first state
        the player controls, through PyBoy's game wrapper, which saves that
        state for `reset` to load.

        Raises:
            Exception: Where the cartridge holds Pokémon Red, since the
                       wrapper checks for BLUE as the first name on the
                       first naming screen and RED on the second, the order
                       Pokémon Blue lists them in, where Red lists RED
                       first.
        """
        # A `None` draws DIV from Python's global generator, which `reset` overwrites.
        self.emulator.game_wrapper.start_game(0)
