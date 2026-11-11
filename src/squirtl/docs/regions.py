"""
Defines `Region`, a page under `docs/pages/` carrying a table written from
a declaration in the package, which `squirtl write docs` writes between
a pair of HTML comments named for the table: the settings one subject of
a run reads, from the help `squirtl train` prints for each, the addresses
`Symbol` declares, or the flags `Event` declares. `Page` holds the page of
one command, whose markers hold the parts `Command` writes from its help.
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

    def fill(self, command: Command, name: str) -> str:
        """
        Lays out the table the pair of markers named `name` holds, read from
        the settings `command` takes or from the enum the name gives.
        """
        return table(name, command)

    def line(self, marker: Match[str]) -> int:
        """
        Counts the line `marker` opens on, from 1.
        """
        return self.text.count("\n", 0, marker.start()) + 1

    def pairs(self) -> list[tuple[Match[str], ...]]:
        """
        Pairs each opening marker on the page with the closing one after it.

        Raises:
            SyntaxError: Where a marker is not one opening followed by its
                         closing, naming the page and the line.
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
                        f"`{self.path}` holds an unpaired marker",
                        (str(self.path), self.line(pair[-1]), None, None)
                    )

        return pairs

    def pieces(
        self,
        command : Command,
        pairs   : Iterable[tuple[Match[str], ...]]
    ) -> Iterable[str]:
        """
        Yields the page's text outside each pair of markers, and each pair
        holding what `fill` lays out for its name.
        """
        last = 0

        for opening, closing in pairs:
            yield self.text[last:opening.end()]
            yield "\n\n" + self.fill(command, opening[2]) + "\n\n"
            last = closing.start()

        yield self.text[last:]

    def written(self, command: Command) -> str:
        """
        Writes what each pair of markers names between them, a subject's
        settings read from those `command` takes, leaving the rest of the
        page as it stands.

        Raises:
            SyntaxError: Where a marker is not one opening followed by
                         its closing, naming the page and the line, before
                         anything is written.
        """
        return "".join(self.pieces(command, self.pairs()))


class Page(Region):
    """
    The page of one command under `docs/pages/commands/`, holding prose of
    its own around a pair of comments for each part `Command.parts` lays
    out, `<!-- help -->` opening the part and `<!-- /help -->` closing it
    where the name is `help` or `settings`.
    """

    marker: ClassVar[Pattern[str]] = compile(r"<!-- (/?)(help|settings) -->")

    def fill(self, command: Command, name: str) -> str:
        """
        Lays out the part of `command` the pair of markers named `name`
        holds.
        """
        return command.parts[name]

    @classmethod
    def read(cls, command: Command) -> Self:
        """
        Reads the page of `command`, or where none exists yet, a page
        holding an empty pair of markers for each part `Command.parts` lays
        out and no prose.
        """
        return cls(
            path = command.path,
            text = command.path.read_text(encoding="utf-8")
                if command.path.is_file()
                else "\n\n".join(
                    f"<!-- {name} -->\n<!-- /{name} -->" for name in command.parts
                ) + "\n"
        )

    def written(self, command: Command) -> str:
        """
        Writes each part of `command` between its pair of markers, leaving
        the page's prose as it stands.

        Raises:
            SyntaxError: Where a marker is not one opening followed by its
                         closing, or where the pairs do not name the parts
                         of `command` in order, each pair once, naming the
                         page and the line of its first marker where it
                         holds one, before anything is written.
        """
        pairs = self.pairs()

        if (names := [opening[2] for opening, _ in pairs]) != list(command.parts):
            raise SyntaxError(
                f"`{self.path}` holds markers naming {', '.join(names) or 'nothing'} "
                f"rather than {', '.join(command.parts)}",
                (str(self.path), self.line(pairs[0][0]) if pairs else None, None, None)
            )

        return "".join(self.pieces(command, pairs))


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
