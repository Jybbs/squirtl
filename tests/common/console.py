"""
Defines `StandIn`, which records each call `GameBoy` makes on `PyBoy` and
each read of its screen, beside `set_event` and `stand`, which set a flag
and the player's position in the memory of `StandIn` or of `PyBoy`, and
`shade`, which draws every gray PyBoy draws into a console's next frame.
"""

from collections.abc import MutableSequence
from numpy           import arange, tile, uint8
from numpy.random    import default_rng
from types           import SimpleNamespace
from typing          import BinaryIO

from squirtl.emulator.console import GameBoy
from squirtl.emulator.schemas import Symbol
from squirtl.reward.schemas   import Event, Position


class StandIn:
    """
    Stands in for `PyBoy`, holding the arguments it was built with, each
    call a `GameBoy` makes on it and each read of its screen in the order
    it made them, the 64 KiB the console addresses with zero in every byte
    until a test writes one, and an RGBA frame whose every pixel holds each
    channel's index in that channel.
    """

    def __init__(self, gamerom: object, **options: object):
        """
        Records `gamerom` and every keyword option a boot passes.
        """
        self.calls   = []
        self.frame   = tile(arange(4, dtype=uint8), (144, 160, 1))
        self.gamerom = gamerom
        self.memory  = bytearray(0x10000)
        self.options = options

    @property
    def game_wrapper(self) -> SimpleNamespace:
        """
        Builds a stand-in for the game wrapper, whose `start_game` and
        `reset_game` each record their call beside the `timer_div` it took.
        """
        return SimpleNamespace(
            reset_game = lambda timer_div: self.calls.append(("reset_game", timer_div)),
            start_game = lambda timer_div: self.calls.append(("start_game", timer_div))
        )

    @property
    def screen(self) -> SimpleNamespace:
        """
        Records a read of the screen.

        Returns:
            An object whose `ndarray` is `frame`, as `PyBoy.screen` holds the
            frame PyBoy last rendered.
        """
        self.calls.append(("screen",))

        return SimpleNamespace(ndarray=self.frame)

    def button(self, input: str, delay: int = 1):
        """
        Records the press of the button `input` names beside the frames
        `delay` holds it for.
        """
        self.calls.append(("button", input, delay))

    def save_state(self, file_like_object: BinaryIO):
        """
        Records a save and writes the memory into `file_like_object`.
        """
        self.calls.append(("save_state",))
        file_like_object.write(self.memory)

    def stop(self, save: bool):
        """
        Records a stop beside whether it saved.
        """
        self.calls.append(("stop", save))

    def tick(self, count: int):
        """
        Records an advance of `count` frames.
        """
        self.calls.append(("tick", count))


def set_event(event: Event, memory: MutableSequence[int]):
    """
    Sets bit `event % 8` of the byte `event // 8` past `wEventFlags` in
    `memory`, as pret/pokered's `SetEvent` macro does, leaving every other
    bit as it was.
    """
    byte, bit = divmod(event, 8)

    memory[Symbol.W_EVENT_FLAGS + byte] |= 1 << bit


def shade(game_boy: GameBoy):
    """
    Draws each of the four grays PyBoy's default palette holds into the next
    frame `game_boy` renders, at the addresses Pan Docs gives:

    - Plays 120 frames, past the 65th, where PyBoy's boot ROM hands the
      cartridge the CPU
    - Fills the 256 tiles the background draws from, at `0x8000` under the
      LCDC the boot ROM leaves, with bytes a generator seeded at 0 draws
    - Writes `0xE4` into BGP at `0xFF47`, drawing each color in the shade of
      its own index
    """
    game_boy.press(None, 120)

    memory                = game_boy.emulator.memory
    memory[0x8000:0x9000] = default_rng(0).integers(256, size=0x1000).tolist()
    memory[0xFF47]        = 0xE4


def stand(memory: MutableSequence[int], position: Position):
    """
    Stands the player on `position` by writing its map and coordinates into
    `wCurMap`, `wXCoord`, and `wYCoord` in `memory`.
    """
    memory[Symbol.W_CUR_MAP] = position.map
    memory[Symbol.W_X_COORD] = position.x
    memory[Symbol.W_Y_COORD] = position.y
