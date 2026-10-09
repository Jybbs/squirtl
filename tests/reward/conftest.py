"""
Defines the fixtures the tests of `squirtl.reward` share, meaning a console
whose memory a test writes, the writers that move the player and set a flag
there, the settings a test scores under, and the progress of an episode
starting on that console under them.
"""

from collections.abc import Callable
from common.console  import StandIn
from pytest          import fixture

from squirtl.emulator.console import GameBoy
from squirtl.emulator.schemas import Symbol
from squirtl.reward.progress  import Progress
from squirtl.reward.schemas   import Event, Position, RewardSettings


@fixture
def flag(game_boy: GameBoy) -> Callable[[Event], None]:
    """
    Builds a writer that sets the flag of the event it is given in the
    console's memory, meaning bit `index % 8` of the byte `index // 8` bytes
    past `wEventFlags`, as pret/pokered's `SetEvent` macro does.
    """
    def set_event(event: Event):
        """
        Sets the flag of `event`, leaving every other bit as it was.
        """
        byte, bit = divmod(event, 8)
        game_boy.emulator.memory[Symbol.W_EVENT_FLAGS + byte] |= 1 << bit

    return set_event


@fixture
def game_boy() -> GameBoy:
    """
    Builds a console over `StandIn`, whose memory holds zero in every byte,
    so the player stands at `x` 0 and `y` 0 on map 0 with no flag set.
    """
    return GameBoy(StandIn(None))


@fixture
def move(game_boy: GameBoy) -> Callable[[Position], None]:
    """
    Builds a writer that stands the player on the position it is given, by
    writing its map and coordinates at the symbols the game holds them in.
    """
    def stand(position: Position):
        """
        Writes `position` into `wCurMap`, `wXCoord`, and `wYCoord`.
        """
        game_boy.emulator.memory[Symbol.W_CUR_MAP] = position.map
        game_boy.emulator.memory[Symbol.W_X_COORD] = position.x
        game_boy.emulator.memory[Symbol.W_Y_COORD] = position.y

    return stand


@fixture
def progress(game_boy: GameBoy, settings: RewardSettings) -> Progress:
    """
    Starts the progress of an episode on `game_boy` under `settings`, with
    the player at `x` 0 and `y` 0 on map 0 and no flag set.
    """
    return Progress(game_boy, settings)


@fixture
def settings() -> RewardSettings:
    """
    Builds settings whose terms pay values apart from the defaults and from
    one another, each a power of two so every sum a step earns is exact.
    """
    return RewardSettings(milestone=0.125, novelty=0.0625, starter=0.5)
