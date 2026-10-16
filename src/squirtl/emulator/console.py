"""
Defines `GameBoy`, which runs a verified cartridge through PyBoy, beside
the protocols naming the PyBoy members it calls: `Emulator`, `GameWrapper`,
`Memory`, and `Screen`.
"""

from contextlib import AbstractContextManager
from io         import BytesIO
from numpy      import ndarray
from pyboy      import PyBoy
from typing     import BinaryIO, Protocol, Self

from squirtl.emulator.schemas import Button, Cartridge, EmulatorSettings, Symbol


class GameWrapper(Protocol):
    """
    The members of `PyBoy.game_wrapper` that `GameBoy` calls.
    """

    def reset_game(self, timer_div: int | None = None):
        """
        Loads the state `start_game` saved, then writes `timer_div` into
        DIV.
        """

    def start_game(self, timer_div: int | None = None):
        """
        Plays the intro to the first playable state and saves it, then
        writes `timer_div` into DIV.
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
    The members of `PyBoy.screen` that `GameBoy` reads.
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


class GameBoy(AbstractContextManager):
    """
    The console running a verified cartridge through the emulator it
    composes, pressing at most one button a step and reading the game's
    memory.
    """

    def __exit__(self, *raised: object):
        """
        Closes the console on leaving a `with` block, whether or not the
        block raised.
        """
        self.close()

    def __init__(self, emulator: Emulator, settings: EmulatorSettings):
        """
        Composes `emulator`, `PyBoy` or a test's stand-in, pressing for the
        `hold` that `settings` names.
        """
        self.emulator = emulator
        self.settings = settings

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
        Starts PyBoy on the bytes of `cartridge`, which give it no path to a
        `.ram`, `.rtc`, or `.sym` file, with sound off and no window unless
        `settings` opens one. It logs errors alone, since its default level
        warns at every boot that Pillow is missing.
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
        writes battery RAM beside the cartridge's path, and for one handed
        over as bytes prints a `TypeError` and keeps running.
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
        Loads the state `start` saved and writes `timer_div` into DIV,
        the counter pret/pokered's `Random_` reads into the game's random
        numbers each frame.
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
        Plays the intro to Red's bedroom through PyBoy's game wrapper, which
        renders none of its frames and saves that state for `reset`, writing
        0 into DIV until `reset` writes each episode's `timer_div`.
        """
        # `start_game` navigates the naming screens of Pokémon Blue alone.
        self.emulator.game_wrapper.start_game(0)
