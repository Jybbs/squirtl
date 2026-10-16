"""
Defines `Progress`, the positions an episode has reached and the flags set
in it, which scores each step and lays both out for the observation.
"""

from collections import Counter
from numpy       import array, int8, ndarray, zeros

from squirtl.emulator.console import GameBoy
from squirtl.reward.schemas   import Event, Position, RewardSettings, Score, Term


class Progress:
    """
    The progress one episode has made toward the starter, meaning each
    position reached, the one the player stands on, and each `Event` flag
    set, against which `score` pays each step.
    """

    def __init__(self, game_boy: GameBoy, settings: RewardSettings):
        """
        Records the position the player starts the episode on and each flag
        already set, neither of which a step earns.
        """
        self.events    = Event.read(game_boy)
        self.game_boy  = game_boy
        self.position  = Position.read(game_boy)
        self.positions = {self.position}
        self.settings  = settings

    @property
    def flags(self) -> ndarray:
        """
        Marks each flag `Event` names with 1 where set and 0 where not, in
        the order `Event` declares them, in the `int8` `MultiBinary` holds.
        """
        return array([event in self.events for event in Event], int8)

    def grid(self, size: int) -> ndarray:
        """
        Marks each position the episode has reached on the player's map in a
        `size` by `size` grid, one cell per square, the player's own at row
        and column `size // 2`.

        Returns:
            A `(size, size)` array of `int8`, 1 in each reached cell and 0
            elsewhere, rows running down the map and columns across.
        """
        reached = zeros((size, size), int8)
        offsets = array(
            [
                (position.y - self.position.y, position.x - self.position.x)
                for position in self.positions
                if position.map == self.position.map
            ]
        ) + size // 2

        reached[*offsets[((offsets >= 0) & (offsets < size)).all(axis=1)].T] = 1

        return reached

    def score(self) -> Score:
        """
        Reads the position the player stands on and the flags set once a
        step has run, paying novelty where the episode has not reached that
        position before and each flag's term for each flag first set, then
        records both.
        """
        self.position = Position.read(self.game_boy)
        reached       = Event.read(self.game_boy) - self.events
        earned        = Counter(event.term for event in reached)

        earned[Term.NOVELTY] += self.position not in self.positions
        self.events          |= reached
        self.positions.add(self.position)

        return Score(
            shares     = self.settings.shares(earned),
            terminated = Event.EVENT_GOT_STARTER in reached
        )
