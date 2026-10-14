"""
Defines the fixtures the tests of `squirtl.environment` request, meaning a
factory making the wrapped environment on PyBoy from a cartridge holding no
game, and an `Overworld` on `StandIn`, whose memory a test writes.
"""

from collections.abc import Callable, Iterator
from common.console  import StandIn
from contextlib      import ExitStack
from gymnasium       import Env
from pytest          import MonkeyPatch, fixture

from squirtl.emulator              import console
from squirtl.emulator.schemas      import Cartridge, EmulatorSettings
from squirtl.environment.overworld import Overworld
from squirtl.environment.schemas   import EnvironmentSettings
from squirtl.reward.schemas        import RewardSettings


@fixture
def made(cartridge: Cartridge) -> Iterator[Callable[..., Env]]:
    """
    Builds a factory making the environment through `Overworld.make` on
    PyBoy from `cartridge`, under the default settings with any keyword
    setting a field of `EnvironmentSettings`, and closes each one it made
    once the test ends.
    """
    with ExitStack() as stack:

        def make(**environment: object) -> Env:
            """
            Makes the environment `environment` describes, closed with the
            test.
            """
            return stack.enter_context(
                Overworld.make(
                    cartridge,
                    EmulatorSettings(),
                    EnvironmentSettings(**environment),
                    RewardSettings()
                )
            )

        yield make


@fixture
def overworld(
    cartridge   : Cartridge,
    monkeypatch : MonkeyPatch,
    settings    : RewardSettings
) -> Overworld:
    """
    Builds an `Overworld` on `StandIn` in place of `PyBoy`, each press held
    for three frames, each step advancing 20, and the reward paying what
    `settings` pays, so a test reads back each call `GameBoy` makes and
    writes the position and the flags into its memory.
    """
    monkeypatch.setattr(console, "PyBoy", StandIn)

    return Overworld(
        cartridge,
        EmulatorSettings(hold=3),
        EnvironmentSettings(frames_per_step=20),
        settings
    )
