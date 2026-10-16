"""
Defines `Invocation`, what one call to the app exits with, prints, and logs,
and `Invoker`, the type of the `invoke` fixture that makes the call.
"""

from collections.abc import Callable
from dataclasses     import dataclass

type Invoker = Callable[[list[str]], Invocation]


@dataclass(frozen=True)
class Invocation:
    """
    The status one call to the app exits with, what it prints to standard
    output, and what it logs to standard error.
    """

    code   : int | str | None
    log    : str
    output : str
