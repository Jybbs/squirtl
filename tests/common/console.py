"""
Defines `StandIn`, which answers for the members of `PyBoy` that a boot
and a press reach, recording what each call received and each read of the
screen.
"""

from numpy import arange, tile, uint8
from types import SimpleNamespace


class StandIn:
    """
    Stands in for `PyBoy`, holding the arguments it was built with, each
    call a `GameBoy` makes on it and each read of its screen in the order
    it made them, and an RGBA frame whose every pixel holds each channel's
    index in that channel.
    """

    def __init__(self, gamerom: object, **options: object):
        """
        Records `gamerom` and every keyword option a boot passes.
        """
        self.calls   = []
        self.frame   = tile(arange(4, dtype=uint8), (144, 160, 1))
        self.gamerom = gamerom
        self.options = options

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

    def button(self, input: str):
        """
        Records the press of the button `input` names.
        """
        self.calls.append(("button", input))

    def tick(self, count: int):
        """
        Records an advance of `count` frames.
        """
        self.calls.append(("tick", count))
