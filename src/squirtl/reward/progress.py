"""
Defines `Progress`, the positions one episode has reached and the flags set
in it, which scores each step on what that step adds and lays both out as
arrays an observation carries.
"""

from collections import Counter
from numpy       import array, ndarray, uint8, zeros

from squirtl.emulator.console import GameBoy
from squirtl.reward.schemas   import Event, Position, RewardSettings, Score, Term


class Progress:
    """
    The progress one episode has made toward the starter, meaning each
    position the player has reached in it, the one the player stands on,
    and each flag `Event` names that is set, which `score` pays each step
    against before recording what the step added.
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
        Marks each flag `Event` names with 1 where it is set and 0 where it
        is not, in the order `Event` declares them.
        """
        return array([event in self.events for event in Event], uint8)

    def grid(self, size: int) -> ndarray:
        """
        Marks each position the episode has reached on the map the player
        stands on in a `size` by `size` grid of squares, one cell per
        square, with the player's own square at row and column `size // 2`.

        Returns:
            A `(size, size)` array of `uint8`, 1 in each cell the episode has
            reached and 0 in every other, rows running down the map and
            columns across it.
        """
        reached = zeros((size, size), uint8)
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
