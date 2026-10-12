"""
Defines `StandIn`, which stands in for the members of `PyBoy` that a boot, a
press, a read of memory, the game wrapper, and a stop reach, recording what
each call received and each read of the screen, beside the writes that stand
the player on a position and set a flag in its memory.
"""

from numpy import arange, tile, uint8
from types import SimpleNamespace

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
        Stands in for the game wrapper, recording each call of its
        `start_game` and `reset_game` beside the `timer_div` it received.

        Returns:
            An object whose `start_game` and `reset_game` record their call,
            as `PyBoy.game_wrapper` holds the wrapper of the game loaded.
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

    def set_event(self, event: Event):
        """
        Sets the flag of `event` in memory as pret/pokered's `SetEvent`
        macro does, meaning bit `index % 8` of the byte `index // 8` bytes
        past `wEventFlags`, leaving every other bit as it was.
        """
        byte, bit = divmod(event, 8)

        self.memory[Symbol.W_EVENT_FLAGS + byte] |= 1 << bit

    def stand(self, position: Position):
        """
        Stands the player on `position` by writing its map and coordinates
        into `wCurMap`, `wXCoord`, and `wYCoord`.
        """
        self.memory[Symbol.W_CUR_MAP] = position.map
        self.memory[Symbol.W_X_COORD] = position.x
        self.memory[Symbol.W_Y_COORD] = position.y

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
