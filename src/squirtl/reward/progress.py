"""
Defines `Progress`, the positions an episode has reached, the flags set in
it, and the terms its steps have earned, which scores each step and lays the
positions and flags out for the observation.
"""

from collections import Counter
from math        import fsum
from numpy       import array, int8, ndarray, zeros

from squirtl.emulator.console import GameBoy
from squirtl.reward.schemas   import Event, Position, RewardSettings, Score, Tally, Term


class Progress:
    """
    The progress one episode has made toward the starter, meaning each
    position reached, the one the player stands on, each `Event` flag set,
    and how often its steps have earned each term, against which `score`
    pays each step.
    """

    def __init__(
        self,
        game_boy : GameBoy,
        settings : RewardSettings,
        tally    : Tally | None = None
    ):
        """
        Takes up the episode where `tally` leaves it, or otherwise records
        the position the player starts the episode on and each flag already
        set, neither of which a step earns.
        """
        tally = tally or Tally.read(game_boy)

        self.earned    = Counter(tally.earned)
        self.events    = set(tally.events)
        self.game_boy  = game_boy
        self.position  = tally.position
        self.positions = tally.reached
        self.settings  = settings

    @property
    def flags(self) -> ndarray:
        """
        Marks each flag `Event` names with 1 where set and 0 where not, in
        the order `Event` declares them, in the `int8` `MultiBinary` holds.
        """
        return array([event in self.events for event in Event], int8)

    @property
    def milestones(self) -> float:
        """
        Totals the reward the flags set in the episode have earned, each
        paid as its term pays it, leaving out the novelty of every position.
        """
        return fsum(
            share for term, share in self.shares.items() if term is not Term.NOVELTY
        )

    @property
    def shares(self) -> dict[Term, float]:
        """
        Totals each term's part of the reward the episode's steps have
        earned, as `RewardSettings.shares` pays the count of each.
        """
        return self.settings.shares(self.earned)

    @property
    def tally(self) -> Tally:
        """
        Packs the progress so far into the `Tally` that `Progress` resumes
        from.
        """
        return Tally.of(self.earned, self.events, self.position, self.positions)

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
        records the position, the flags, and the terms earned.
        """
        self.position = Position.read(self.game_boy)
        reached       = Event.read(self.game_boy) - self.events
        earned        = Counter(event.term for event in reached)

        earned[Term.NOVELTY] += self.position not in self.positions
        self.events          |= reached
        self.earned.update(earned)
        self.positions.add(self.position)

        return Score(
            shares     = self.settings.shares(earned),
            terminated = Event.EVENT_GOT_STARTER in reached
        )
