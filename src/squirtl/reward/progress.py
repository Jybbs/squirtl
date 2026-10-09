"""
Defines `Progress`, the positions one episode has reached and the flags set
in it, which scores each step on what that step adds.
"""

from collections import Counter

from squirtl.emulator.console import GameBoy
from squirtl.reward.schemas   import Event, Position, RewardSettings, Score, Term


class Progress:
    """
    The progress one episode has made toward the starter, meaning each
    position the player has reached in it and each flag `Event` names that
    is set, which `score` pays each step against before recording what the
    step added.
    """

    def __init__(self, game_boy: GameBoy, settings: RewardSettings):
        """
        Records the position the player starts the episode on and each flag
        already set, neither of which a step earns.
        """
        self.events    = Event.read(game_boy)
        self.game_boy  = game_boy
        self.positions = {Position.read(game_boy)}
        self.settings  = settings

    def score(self) -> Score:
        """
        Reads the position the player stands on and the flags set once a
        step has run, paying novelty where the episode has not reached that
        position before and each flag's term for each flag first set, then
        records both.
        """
        position = Position.read(self.game_boy)
        reached  = Event.read(self.game_boy) - self.events
        earned   = Counter(event.term for event in reached)

        earned[Term.NOVELTY] += position not in self.positions
        self.events          |= reached
        self.positions.add(position)

        return Score(
            shares = {term: earned[term] * self.settings.pay(term) for term in Term},
            terminated = Event.EVENT_GOT_STARTER in reached
        )
