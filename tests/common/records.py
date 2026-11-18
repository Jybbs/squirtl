"""
Defines `ranges`, which reads the fields a record of settings types as a
`Range`, so a case refusing each one covers a field the record adds, and
`idled`, the episode a demonstration on the cartridge `timed` writes holds.
"""

from pydantic import BaseModel
from typing   import get_origin

from squirtl.emulator.schemas    import Range
from squirtl.environment.schemas import Recording
from squirtl.reward.schemas      import Term
from squirtl.runs.schemas        import Episode


def idled() -> Episode:
    """
    Builds the episode reaching the starter of the cartridge `timed` writes
    after 13 idle presses at a `timer_div` of 0, each advancing 64 frames.
    """
    return Episode(
        epsilon    = None,
        length     = 13,
        positions  = 1,
        recording  = Recording(presses=bytes(13), timer_div=0),
        reward     = 0.8,
        seconds    = 1.0,
        shares     = {Term.GOAL: 0.6, Term.MILESTONE: 0.2, Term.NOVELTY: 0.0},
        terminated = True,
        update     = None
    )


def ranges(record: type[BaseModel]) -> list[str]:
    """
    Reads the name of each field of `record` its declaration types as a
    `Range`, in the order it declares them.
    """
    return [
        name
        for name, field in record.model_fields.items()
        if get_origin(field.annotation) is Range
    ]
