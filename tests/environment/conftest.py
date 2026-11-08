"""
Defines the fixtures the tests of `squirtl.environment` request, `made`,
which makes the wrapped environment on PyBoy, `following`, which makes
it along a demonstration on the cartridge `timed` writes, `overworld`, an
`Overworld` on `StandIn`, `shaded`, an `Overworld` on PyBoy whose frame
holds all four of its grays, and `walking`, which moves the player along
each tick of `overworld`.
"""

from collections.abc import Callable, Iterator
from common.console  import StandIn, shade
from contextlib      import ExitStack
from gymnasium       import Env
from pytest          import MonkeyPatch, fixture

from squirtl.emulator              import console
from squirtl.emulator.schemas      import Cartridge, EmulatorSettings, Symbol
from squirtl.environment.overworld import Overworld
from squirtl.environment.schemas   import EnvironmentSettings, Recording
from squirtl.reward.schemas        import RewardSettings


@fixture
def made(cartridge: Cartridge) -> Iterator[Callable[..., Env]]:
    """
    Builds a factory making the environment on PyBoy from `cartridge`
    through the spec `Overworld.specification` gives under the default
    settings, any keyword setting a field of `EnvironmentSettings`, and
    closing each with the test.
    """
    with ExitStack() as stack:

        def make(**environment: object) -> Env:
            """
            Makes the environment `environment` describes.
            """
            return stack.enter_context(
                Overworld.specification(
                    cartridge,
                    EmulatorSettings(),
                    EnvironmentSettings(**environment),
                    RewardSettings()
                ).make()
            )

        yield make


@fixture
def following(timed: Cartridge) -> Iterator[Callable[..., Env]]:
    """
    Builds a factory making the environment on PyBoy from `timed` along the
    demonstration of 13 idle presses at a `timer_div` of 0, or the presses
    it is given, each step advancing 64 frames, so the presses at steps 4,
    8, and 12 set the cartridge's flags, the last reaching the starter, and
    closing each with the test.
    """
    with ExitStack() as stack:

        def make(presses: bytes = bytes(13), tolerance: float = 0.0) -> Env:
            """
            Makes the environment along the demonstration of `presses`.
            """
            return stack.enter_context(
                Overworld.specification(
                    timed,
                    EmulatorSettings(),
                    EnvironmentSettings(frames_per_step=64),
                    RewardSettings(),
                    Recording(presses=presses, timer_div=0),
                    tolerance
                ).make()
            )

        yield make


@fixture
def overworld(
    cartridge   : Cartridge,
    monkeypatch : MonkeyPatch,
    settings    : RewardSettings
) -> Overworld:
    """
    Builds an `Overworld` on `StandIn` with each press held three frames,
    each step advancing 20, and the reward paying `settings`, so a test
    reads each call `GameBoy` makes and writes into its memory.
    """
    monkeypatch.setattr(console, "PyBoy", StandIn)

    return Overworld(
        cartridge,
        EmulatorSettings(hold=3),
        EnvironmentSettings(frames_per_step=20),
        settings
    )


@fixture
def shaded(made: Callable[..., Env]) -> Overworld:
    """
    Makes the environment on PyBoy and resets it, draws all four of PyBoy's
    grays into its next frame through `shade`, then steps it once.

    Returns:
        The unwrapped `Overworld`, whose `game_boy.grayscale` holds the frame
        that step observes.
    """
    env = made()
    env.reset(seed=0)
    shade(env.unwrapped.game_boy)
    env.unwrapped.step(0)

    return env.unwrapped


@fixture
def walking(monkeypatch: MonkeyPatch, overworld: Overworld):
    """
    Makes each tick of the stand-in under `overworld` move the player one
    square right on the map it stands on, recording the tick as before.
    """
    emulator = overworld.game_boy.emulator

    def tick(count: int):
        """
        Records an advance of `count` frames and moves the player a square.
        """
        emulator.calls.append(("tick", count))
        emulator.memory[Symbol.W_X_COORD] += 1

    monkeypatch.setattr(emulator, "tick", tick)
