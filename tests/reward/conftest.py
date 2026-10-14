"""
Defines the fixtures the tests of `squirtl.reward` share, meaning a console
whose memory a test writes, the writers that move the player and set a flag
there, and the progress of an episode starting on that console under the
reward settings `tests/conftest.py` builds.
"""

from collections.abc import Callable
from common.console  import StandIn, set_event, stand
from functools       import partial
from pytest          import fixture

from squirtl.emulator.console import GameBoy
from squirtl.emulator.schemas import EmulatorSettings
from squirtl.reward.progress  import Progress
from squirtl.reward.schemas   import Event, Position, RewardSettings


@fixture
def flag(game_boy: GameBoy) -> Callable[[Event], None]:
    """
    Builds a writer that sets the flag of the event it is given in the
    console's memory through `set_event`.
    """
    return partial(set_event, memory=game_boy.emulator.memory)


@fixture
def game_boy() -> GameBoy:
    """
    Builds a console over `StandIn`, whose memory holds zero in every byte,
    so the player stands at `x` 0 and `y` 0 on map 0 with no flag set.
    """
    return GameBoy(StandIn(None), EmulatorSettings())


@fixture
def move(game_boy: GameBoy) -> Callable[[Position], None]:
    """
    Builds a writer that stands the player on the position it is given in
    the console's memory through `stand`.
    """
    return partial(stand, game_boy.emulator.memory)


@fixture
def progress(game_boy: GameBoy, settings: RewardSettings) -> Progress:
    """
    Starts the progress of an episode on `game_boy` under `settings`, with
    the player at `x` 0 and `y` 0 on map 0 and no flag set.
    """
    return Progress(game_boy, settings)
