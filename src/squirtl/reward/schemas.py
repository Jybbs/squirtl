"""
Defines the records the reward reads and writes:

- `Term`, the terms a step's reward sums
- `Event`, the flags in `wEventFlags` marking the way to the starter
- `Position`, the square of the map the player stands on
- `RewardSettings`, what each term pays a step
- `Score`, the reward one step earns, split by term
"""

from collections     import Counter
from collections.abc import Mapping
from enum            import IntEnum, StrEnum, auto
from math            import fsum
from pydantic        import Field, model_validator
from typing          import Annotated, Self

from squirtl.emulator.console import GameBoy
from squirtl.emulator.schemas import Record, Symbol

type Pay = Annotated[float, Field(ge=0, le=1)]


class Position(Record):
    """
    The square of 2x2 tiles the player stands on, named by the map holding
    it and its coordinates there, so two positions are equal only where all
    three are.
    """

    map: int
    """
    The map holding the square, as `wCurMap` holds it.
    """

    x: int
    """
    The square's column in that map, as `wXCoord` holds it.
    """

    y: int
    """
    The square's row in that map, as `wYCoord` holds it.
    """

    @classmethod
    def read(cls, game_boy: GameBoy) -> Self:
        """
        Reads the position the player stands on from the game's memory.
        """
        return cls(
            map = game_boy.read(Symbol.W_CUR_MAP),
            x   = game_boy.read(Symbol.W_X_COORD),
            y   = game_boy.read(Symbol.W_Y_COORD)
        )


class Term(StrEnum):
    """
    The terms a step's reward sums, each member's value the name of the
    field of `RewardSettings` holding what it pays and the key of its share
    in `Score.shares`.
    """

    MILESTONE = auto()
    NOVELTY   = auto()
    STARTER   = auto()


class Event(IntEnum):
    """
    The flags in `wEventFlags` marking the milestones on the way to the
    starter and the starter itself, each member named for its constant
    in pret/pokered's `constants/event_constants.asm` and its value that
    constant's index in the flag array.
    """

    EVENT_FOLLOWED_OAK_INTO_LAB   = 0x00
    EVENT_GOT_STARTER             = 0x22
    EVENT_OAK_APPEARED_IN_PALLET  = 0x27
    EVENT_OAK_ASKED_TO_CHOOSE_MON = 0x21

    @property
    def term(self) -> Term:
        """
        Names the term the step first setting the flag earns, `STARTER` for
        `EVENT_GOT_STARTER` and `MILESTONE` for every other flag.
        """
        return Term.STARTER if self is Event.EVENT_GOT_STARTER else Term.MILESTONE

    def is_set(self, game_boy: GameBoy) -> bool:
        """
        Reads the flag from the game's memory as pret/pokered's `CheckEvent`
        macro does, meaning bit `index % 8` of the byte `index // 8` bytes
        past `wEventFlags`.
        """
        byte, bit = divmod(self, 8)

        return bool(game_boy.read(Symbol.W_EVENT_FLAGS, byte) >> bit & 1)

    @classmethod
    def read(cls, game_boy: GameBoy) -> set[Self]:
        """
        Reads which of the flags are set in the game's memory.
        """
        return {event for event in cls if event.is_set(game_boy)}


class RewardSettings(Record):
    """
    The settings the reward reads, each a field of `RunSettings.reward` and
    a key under `[tool.squirtl.reward]` in `pyproject.toml`, holding what
    each member of `Term` pays a step.
    """

    milestone: Pay = 0.1
    """
    The reward a step earns for each milestone on the way to the starter
    whose flag it first sets.
    """

    novelty: Pay = 0.005
    """
    The reward a step earns for reaching a position the episode has not
    reached before, whose default is the reward Pleines et al. pay for each
    new coordinate.
    """

    starter: Pay = 0.6
    """
    The reward the step first setting `EVENT_GOT_STARTER` earns, which has
    to be the largest term.
    """

    @property
    def ceiling(self) -> float:
        """
        Totals the shares of a step reaching a new position and first
        setting every flag `Event` names at once, the most any step can
        earn, since every other step earns each term no more often.
        """
        earned = Counter([Term.NOVELTY, *(event.term for event in Event)])

        return fsum(self.shares(earned).values())

    def pay(self, term: Term) -> float:
        """
        Reads what `term` pays a step.
        """
        return getattr(self, term)

    def shares(self, earned: Mapping[Term, int]) -> dict[Term, float]:
        """
        Multiplies what each term pays by the number of times `earned`
        counts it, giving zero for a term `earned` leaves out.
        """
        return {term: earned.get(term, 0) * self.pay(term) for term in Term}

    @model_validator(mode="after")
    def verify(self) -> Self:
        """
        Refuses a starter paying no more than another term, and terms whose
        `ceiling` passes 1, the bound Mnih et al. clip each reward to.

        Raises:
            ValueError: Where either holds, which Pydantic raises as a
                        `ValidationError`.
        """
        if self.starter <= max(self.milestone, self.novelty):
            raise ValueError(
                f"the starter pays {self.starter}, no more than the milestone at "
                f"{self.milestone} or the novelty at {self.novelty}, where it has "
                f"to be the largest term"
            )

        if self.ceiling > 1:
            raise ValueError(
                f"a step reaching a new position and every event at once earns "
                f"{self.ceiling - 1:.3g} more than the 1 Mnih et al. clip each "
                f"reward to"
            )

        return self


class Score(Record):
    """
    The reward one step earns, split by the term paying each part, beside
    whether the step ends the episode.
    """

    shares: dict[Term, float]
    """
    Each term's part of the step's reward, zero for a term the step did not
    earn.
    """

    terminated: bool
    """
    Whether the step first set `EVENT_GOT_STARTER`, which ends the episode.
    """

    @property
    def total(self) -> float:
        """
        Sums the shares into the step's reward, rounding once at the end as
        `fsum` does.
        """
        return fsum(self.shares.values())
