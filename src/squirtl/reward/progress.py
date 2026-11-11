"""
Defines `Progress`, the positions an episode has reached, the flags set in
it, and the terms its steps have earned, which scores each step and lays the
positions and flags out for the observation.
"""

from collections import Counter
from numpy       import array, int8, ndarray, zeros

from squirtl.emulator.console import GameBoy
from squirtl.reward.schemas   import Event, Position, RewardSettings, Score, Tally, Term


class Progress:
    """
    The progress one episode has made toward its goal, meaning each position
    reached, the one the player stands on, each `Event` flag set, the step
    first setting each flag the episode's own steps set, and how often its
    steps have earned each term, against which `score` pays each step.
    """

    def __init__(
        self,
        game_boy : GameBoy,
        goal     : Event,
        settings : RewardSettings,
        tally    : Tally | None = None
    ):
        """
        Takes up the episode where `tally` leaves it, or otherwise records
        the position the player starts the episode on and each flag already
        set, neither of which a step earns, and the term each flag up to
        `goal` pays.
        """
        tally = tally or Tally.read(game_boy)

        self.earned    = Counter(tally.earned)
        self.events    = set(tally.events)
        self.firsts    = dict(tally.firsts)
        self.game_boy  = game_boy
        self.position  = tally.position
        self.positions = tally.reached
        self.settings  = settings
        self.steps     = tally.steps
        self.terms     = goal.terms

    @property
    def flags(self) -> ndarray:
        """
        Marks each flag `Event` names with 1 where set and 0 where not, in
        the order `Event` declares them, in the `int8` `MultiBinary` holds.
        """
        return array([event in self.events for event in Event], int8)

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
        return Tally.of(
            self.earned,
            self.events,
            self.firsts,
            self.position,
            self.positions,
            self.steps
        )

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
        position before and, for each flag first set up to the goal, the
        term `Event.terms` names, then records the position, the flags,
        the step first setting each, and the terms earned. The step first
        setting the goal ends the episode.
        """
        self.steps   += 1
        self.position = Position.read(self.game_boy)
        reached       = Event.read(self.game_boy) - self.events
        earned        = Counter(
            self.terms[event] for event in reached & self.terms.keys()
        )

        earned[Term.NOVELTY] += self.position not in self.positions
        self.events          |= reached
        self.earned.update(earned)
        self.firsts.update(dict.fromkeys(reached, self.steps))
        self.positions.add(self.position)

        return Score(
            shares     = self.settings.shares(earned),
            terminated = Term.GOAL in earned
        )
