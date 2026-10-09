"""
Defines `StandIn`, which answers for the members of `PyBoy` that a boot and
a press reach, recording what each call received.
"""

from numpy import arange, tile, uint8
from types import SimpleNamespace


class StandIn:
    """
    Stands in for `PyBoy`, holding the arguments it was built with, each
    call a `GameBoy` makes on it in the order it made them, and an RGBA
    screen whose every pixel holds each channel's index in that channel.
    """

    def __init__(self, gamerom: object, **options: object):
        """
        Records `gamerom` and every keyword option a boot passes.
        """
        self.calls   = []
        self.gamerom = gamerom
        self.options = options
        self.screen  = SimpleNamespace(
            ndarray = tile(arange(4, dtype=uint8), (144, 160, 1))
        )

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
