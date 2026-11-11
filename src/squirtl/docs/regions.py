"""
Defines `Region`, a page under `docs/pages/` carrying a table written from
a declaration in the package, which `squirtl write docs` writes between a
pair of HTML comments named for the table: the settings one subject of a run
reads, from the help `squirtl train` prints for each, the addresses `Symbol`
declares, or the flags `Event` declares.
"""

from collections.abc import Iterable, Iterator
from itertools       import batched
from pathlib         import Path
from re              import Match, Pattern, compile
from typing          import ClassVar, Self

from squirtl.docs.commands    import Command
from squirtl.emulator.schemas import Record, Symbol
from squirtl.reward.schemas   import Event


class Region(Record):
    """
    A page under `docs/pages/` holding one or more pairs of comments, each
    `<!-- <name> -->` opening the table `table` lays out for its name and
    `<!-- /<name> -->` closing it, where the name is `settings:<subject>`,
    `symbols`, or `events`.
    """

    marker: ClassVar[Pattern[str]] = compile(
        r"<!-- (/?)(settings:[a-z]+|symbols|events) -->"
    )

    path: Path
    """
    The page, relative to the root of the checkout.
    """

    text: str
    """
    What the page holds on disk.
    """

    @classmethod
    def every(cls, folder: Path = Path("docs/pages")) -> Iterator[Self]:
        """
        Reads each page under `folder` holding a marker, in the order of
        its path.
        """
        for path in sorted(folder.rglob("*.md")):
            if cls.marker.search(text := path.read_text(encoding="utf-8")):
                yield cls(path=path, text=text)

    def line(self, marker: Match[str]) -> int:
        """
        Counts the line `marker` opens on, from 1.
        """
        return self.text.count("\n", 0, marker.start()) + 1

    def pieces(
        self,
        pairs : Iterable[tuple[Match[str], ...]],
        train : Command
    ) -> Iterable[str]:
        """
        Yields the page's text outside each pair of markers, and each pair
        holding the table its name gives.
        """
        last = 0

        for opening, closing in pairs:
            yield self.text[last:opening.end()]
            yield "\n\n" + table(opening[2], train) + "\n\n"
            last = closing.start()

        yield self.text[last:]

    def written(self, train: Command) -> str:
        """
        Writes the table each pair of markers names between them, a
        subject's settings read from those `train` takes, leaving the rest
        of the page as it stands.

        Raises:
            SyntaxError: Where a marker is not one opening followed by its
                         closing, naming the page and the line, before any
                         table is written.
        """
        pairs = list(batched(self.marker.finditer(self.text), 2))

        for pair in pairs:
            match pair:
                case (opening, closing) if (
                    not opening[1] and closing[1] == "/" and opening[2] == closing[2]
                ):
                    continue
                case _:
                    raise SyntaxError(
                        f"{self.path}:{self.line(pair[-1])}: an unpaired marker"
                    )

        return "".join(self.pieces(pairs, train))


def table(name: str, train: Command) -> str:
    """
    Lays out the Markdown table a pair of markers named `name` holds:

    - For `settings:<subject>`, each setting under `--<subject>.` that
      `train` takes
    - For `symbols`, each address `Symbol` declares beside its label, in
      the order of the address
    - For `events`, each flag `Event` declares beside its index, in the
      order the opening sets them
    """
    match name.split(":"):
        case ["settings", subject]: return train.table(f"--{subject}.")
        case ["symbols"]:
            header = "| **Address** | **Label** |", "|---|---|"
            rows   = (f"| `0x{symbol:04X}` | `{symbol.label}` |" for symbol in sorted(
                Symbol
            ))
        case _:
            header = "| **Event** | **Index** |", "|---|---|"
            rows   = (f"| `{event.name}` | `0x{event:02X}` |" for event in Event)

    return "\n".join((*header, *rows))
