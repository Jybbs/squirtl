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

    @property
    def messages(self) -> list[str]:
        """
        Splits `log` into the message each line holds, past the time the
        line opens on.
        """
        return [line.partition(" ")[2] for line in self.log.splitlines()]
