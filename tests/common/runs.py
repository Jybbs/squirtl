"""
Defines `Played` and `Unbroken`, the types of the `played` and `unbroken`
fixtures, each reading the run a key names and playing it the first time a
case reads it.
"""

from collections.abc import Callable, Hashable
from pathlib         import Path

from squirtl.runs.schemas import Run

type Played   = Callable[[Hashable, Callable[[], Path]], Path]
type Unbroken = Callable[[Hashable, Callable[[], Run]], Run]
