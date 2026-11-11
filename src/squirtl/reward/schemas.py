"""
Defines the records the reward reads and writes:

- `Term`, the terms a step's reward sums
- `Event`, the flags in `wEventFlags` the opening sets up to the Pokédex,
  which JSON holds as `Flag`, by name
- `Position`, the square of the map the player stands on
- `RewardSettings`, what each term pays a step
- `Score`, the reward one step earns, split by term
"""

from collections     import Counter
from collections.abc import Mapping
from enum            import IntEnum, StrEnum, auto
from itertools       import takewhile
from math            import fsum
from operator        import attrgetter
from pydantic        import PlainSerializer, model_validator
from typing          import Annotated, Self

from squirtl.emulator.console import GameBoy
from squirtl.emulator.schemas import Record, Symbol, UnitInterval

type Flag = Annotated[
    Event, PlainSerializer(attrgetter("name"), return_type=str, when_used="json")
]


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

    GOAL      = auto()
    MILESTONE = auto()
    NOVELTY   = auto()


class Event(IntEnum):
    """
    The flags in `wEventFlags` the opening sets from Blue's bedroom to the
    Pokédex, declared in the order the opening sets them, each member named
    for its constant in pret/pokered's `constants/event_constants.asm` and
    its value that constant's index in the flag array.
    """

    EVENT_OAK_APPEARED_IN_PALLET    = 0x27  # prose: skip[alphabetize-siblings]
    EVENT_FOLLOWED_OAK_INTO_LAB     = 0x00  # prose: skip[alphabetize-siblings]
    EVENT_OAK_ASKED_TO_CHOOSE_MON   = 0x21  # prose: skip[alphabetize-siblings]
    EVENT_GOT_STARTER               = 0x22  # prose: skip[alphabetize-siblings]
    EVENT_BATTLED_RIVAL_IN_OAKS_LAB = 0x23
    EVENT_GOT_OAKS_PARCEL           = 0x39
    EVENT_GOT_POKEDEX               = 0x25

    @property
    def terms(self) -> dict[Self, Term]:
        """
        Names the term each flag pays an episode ending at this one, the
        goal, meaning `MILESTONE` for each flag declared before it and
        `GOAL` for itself, in the order `Event` declares them.
        """
        return dict.fromkeys(
            takewhile(lambda flag: flag is not self, type(self)),
            Term.MILESTONE
        ) | {self: Term.GOAL}

    @classmethod
    def _missing_(cls, value: object) -> Self | None:
        """
        Looks up the member `value` names, spelled as `Event` declares it
        or as cyclopts lists it among a flag's choices, in lowercase with
        hyphens, where no member holds `value`, since both `Event(value)`
        and Pydantic's validation of a member fall back to this hook.
        """
        return cls.__members__.get(str(value).upper().replace("-", "_"))

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
    Whether the step first set the run's goal, which ends the episode.
    """

    @property
    def total(self) -> float:
        """
        Sums the shares into the step's reward, rounding once at the end as
        `fsum` does.
        """
        return fsum(self.shares.values())


class RewardSettings(Record):
    """
    The settings the reward reads, each a field of `RunSettings.reward` and
    a key under `[tool.squirtl.reward]` in `pyproject.toml`, holding what
    each member of `Term` pays a step.
    """

    goal: UnitInterval = 0.35
    """
    The reward the step first setting the run's goal earns, which has to be
    the largest term.
    """

    milestone: UnitInterval = 0.1
    """
    The reward a step earns for each flag on the way to the goal it first
    sets.
    """

    novelty: UnitInterval = 0.00025
    """
    The reward a step earns for reaching a position the episode has not
    reached before, whose default is a 400th of the default milestone, the
    ratio Pleines et al. pay one new coordinate against one completed event.
    """

    def ceiling(self, goal: Event) -> float:
        """
        Totals the shares of a step reaching a new position and first
        setting at once every flag an episode ending at `goal` is paid for,
        the most any of its steps can earn, since every other step earns
        each term no more often.
        """
        return fsum(self.shares(Counter([Term.NOVELTY, *goal.terms.values()])).values())

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

    def total(self, earned: Mapping[Term, int]) -> float:
        """
        Totals the shares of every term `earned` counts but `NOVELTY`,
        meaning what an episode earns for the flags it sets.
        """
        return fsum(self.shares({**earned, Term.NOVELTY: 0}).values())

    @model_validator(mode="after")
    def verify(self) -> Self:
        """
        Refuses a goal paying no more than another term.

        Raises:
            ValueError: Where it does, which Pydantic raises as a
                        `ValidationError`.
        """
        if self.goal <= max(self.milestone, self.novelty):
            raise ValueError(
                f"the goal pays {self.goal}, no more than the milestone at "
                f"{self.milestone} or the novelty at {self.novelty}, where it has "
                f"to be the largest term"
            )

        return self
