"""
Defines `Region`, a page under `docs/pages/` carrying the table of the
settings one subject of a run reads, which `squirtl write docs` writes
between a pair of HTML comments named for the subject, from the help
`squirtl train` prints for each of those settings.
"""

from collections.abc import Iterable, Iterator
from itertools       import batched
from pathlib         import Path
from re              import Match, Pattern, compile
from typing          import ClassVar, Self

from squirtl.docs.commands    import Command
from squirtl.emulator.schemas import Record


class Region(Record):
    """
    A page under `docs/pages/` holding one or more pairs of comments, each
    `<!-- settings:<subject> -->` opening the table of the settings under
    `--<subject>.` and `<!-- /settings:<subject> -->` closing it.
    """

    marker: ClassVar[Pattern[str]] = compile(r"<!-- (/?)settings:([a-z]+) -->")

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
        holding the table of its subject's settings.
        """
        last = 0

        for opening, closing in pairs:
            yield self.text[last:opening.end()]
            yield "\n\n" + train.table(f"--{opening[2]}.") + "\n\n"
            last = closing.start()

        yield self.text[last:]

    def written(self, train: Command) -> str:
        """
        Writes the table of each subject's settings `train` takes between
        its pair of markers, leaving the rest of the page as it stands.

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
