"""
Defines `Region`, a page under `docs/pages/` carrying a table written from
a declaration in the package, which `squirtl write docs` writes between a
pair of HTML comments named for the table: the settings one subject of a run
reads, from the help `squirtl train` prints for each, a part of the site's
identity `Identity` declares, the addresses `Symbol` declares, or the flags
`Event` declares. `Page` holds the page of one command, whose markers hold
the parts `Command` writes from its help, and `Summary` the README, whose
markers hold its sentence on the results.
"""

from collections.abc    import Iterable, Iterator
from importlib.metadata import metadata
from itertools          import batched
from pathlib            import Path
from re                 import Match, Pattern, compile
from typing             import ClassVar, Self

from squirtl.docs.commands    import Command
from squirtl.docs.results     import Results, addresses
from squirtl.emulator.schemas import Record, Symbol
from squirtl.identity.schemas import Color, Identity
from squirtl.markdown.tables  import tabulate
from squirtl.reward.schemas   import Event


class Region(Record):
    """
    A page under `docs/pages/` holding one or more pairs of comments, each
    `<!-- <name> -->` opening the table `table` lays out for its name and
    `<!-- /<name> -->` closing it, where the name is `settings:<subject>`,
    `identity:<field>`, `symbols`, or `events`.
    """

    marker: ClassVar[Pattern[str]] = compile(
        r"<!-- (/?)((?:identity|settings):[a-z]+|symbols|events) -->"
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


class Summary(Region):
    """
    The README, holding its sentence on the results between `<!-- results
    -->` and `<!-- /results -->`, linked to the site's page setting each
    agent against random presses at the `Homepage` address the package
    metadata names.
    """

    marker: ClassVar[Pattern[str]] = compile(r"<!-- (/?)(results) -->")

    results: Results
    """
    The runs the sentence spells.
    """

    def fill(self, command: Command, name: str) -> str:
        """
        Spells the sentence on `results`, after the link to the site's page
        setting each agent against random presses.
        """
        link = f"[Against Random Presses]({addresses()['Homepage']}results/comparison)"

        return f"**{link}** {self.results.summary}"

    @classmethod
    def found(cls, results: Results) -> Iterator[Self]:
        """
        Reads the README beside the `results` its sentence spells, where it
        holds a marker.
        """
        path = Path(".github/README.md")

        if (
            path.is_file()
            and cls.marker.search(text := path.read_text(encoding="utf-8"))
        ):
            yield cls(path=path, results=results, text=text)


def contrast(color: Color, ground: Color) -> str:
    """
    Writes the contrast ratio of `color` on `ground` to two places, as WCAG
    2.2 measures it.
    """
    return f"{color.contrast(ground):.2f}:1"


def identity_table(field: str, identity: Identity) -> str:
    """
    Lays out the Markdown table of the part of `identity` that its field
    `field` declares:

    - For `colors` and `neutrals`, each color's token, name, hex, and
      purpose
    - For `ramp`, each of Denim's steps beside the share of black or white
      it mixes in and its contrast on each ground
    - For `hues`, each step of each hue's ramp on each ground, beside the
      share of the ground, the other ground, or black or white it mixes in
      and its contrast on that ground
    - For `order`, the series hues in the order a chart takes them, each
      beside the role it takes
    - For `sections`, the hue each section takes
    - For `faces`, each face beside the role it takes, what it sets, its
      axes, and its fallback
    - For `logo`, the color each part of the trail takes on each ground,
      then the color each Game Boy shade of a sprite takes
    - For `tagline`, the tagline beside the byline, the summary the
      package's metadata reads from `pyproject.toml`

    Raises:
        ValueError: Where `field` names no part of the identity a table
                    lays out.
    """
    palette = identity.palette
    schemes = identity.schemes
    light   = palette[schemes.light.ground]
    dark    = palette[schemes.dark.ground]

    match field:
        case "colors" | "neutrals":
            return tabulate(
                header = ("Token", "Name", "Hex", "Purpose"),
                rows   = (
                    (f"`{token}`", color.name, f"`{color.hex}`", color.purpose)
                    for token, color in getattr(identity, field).items()
                )
            )
        case "ramp":
            return tabulate(
                header = (
                    "Token", "Name", "Hex", "Mixes In",
                    f"On {light.name}",
                    f"On {dark.name}",
                    "Purpose"
                ),
                rows = (
                    (
                        f"`{token}`",
                        step.name,
                        f"`{step.hex}`",
                        f"{step.share:.0%} {step.toward}",
                        contrast(step, light),
                        contrast(step, dark),
                        step.purpose
                    )
                    for token, step in identity.ramp.items()
                )
            )
        case "hues":
            return tabulate(
                header = ("Hue", "Ground", "Step", "Hex", "Mixes In", "Contrast"),
                rows   = (
                    (
                        identity.colors[hue.token].name,
                        ground.name, step,
                        f"`{hexed}`",
                        mixed,
                        contrast(Color(hex=hexed, name=step, purpose=step), ground)
                    )
                    for hue in identity.hues.values()
                    for scheme, ground, other in (
                        ("light", light, dark),
                        ("dark", dark, light)
                    )
                    for ramp, link in [
                        (
                            getattr(hue, scheme),
                            identity.ramp[getattr(schemes, scheme).link]
                        )
                    ]
                    for step, hexed, mixed in (
                        *(
                            (f"Shade {n}", shade, f"{share:.0%} {ground.name}")
                            for n, (shade, share) in enumerate(
                                zip(ramp.shades, identity.shares),
                                start = 1
                            )
                        ),
                        (
                            "Text", ramp.text,
                            f"{link.share:.0%} {link.toward}" if hue.token == "primary"
                            else f"{ramp.ink:.0%} {other.name}" if ramp.ink
                            else "None"
                        )
                    )
                )
            )
        case "order":
            roles = {hue: role for role, hue in identity.roles.items()}

            return tabulate(
                header = ("Place", "Hue", "Hex", "Role"),
                rows   = (
                    (place, color.name, f"`{color.hex}`", f"`{roles[hue]}`")
                    for place, hue in enumerate(identity.order, start=1)
                    for color in [identity.colors[identity.hues[hue].token]]
                )
            )
        case "sections":
            return tabulate(
                header = ("Section", "Hue", "Hex"),
                rows   = (
                    (folder.capitalize(), color.name, f"`{color.hex}`")
                    for folder, hue in identity.sections.items()
                    for color in [identity.colors[identity.hues[hue].token]]
                )
            )
        case "faces":
            return tabulate(
                header = ("Role", "Family", "Sets", "Axes", "Fallback"),
                rows   = (
                    (
                        role.capitalize(),
                        face.family, face.purpose,
                        f"`{face.axes}`",
                        ", ".join(face.fallback)
                    )
                    for role, face in identity.faces
                )
            )
        case "logo":
            parts = {
                "ahead"   : "The dot still ahead",
                "block"   : "Blue’s block",
                "trail-1" : "The first third, oldest",
                "trail-2" : "The middle third",
                "trail-3" : "The last third, newest"
            }
            named = {
                token: f"{color.name} `{color.hex}`" for token, color in palette.items()
            }
            trail = tabulate(
                header = ("Part", f"On {light.name}", f"On {dark.name}"),
                rows   = (
                    (parts[part], named[on_light], named[on_dark])
                    for part, (on_light, on_dark) in identity.logo.named.items()
                )
            )
            shades = tabulate(
                header = ("Game Boy Shade", "Takes"),
                rows   = ((shade, named[token]) for shade, token in enumerate(
                    identity.logo.shades
                ))
            )

            return f"{trail}\n\n{shades}"
        case "tagline":
            return tabulate(
                header = ("Line", "Text"),
                rows   = (
                    ("Tagline", identity.tagline),
                    ("Byline", metadata("squirtl")["Summary"])
                )
            )
        case _: raise ValueError(f"no identity table is named {field}")


def table(name: str, train: Command) -> str:
    """
    Lays out the Markdown table a pair of markers named `name` holds:

    - For `settings:<subject>`, each setting under `--<subject>.` that
      `train` takes
    - For `identity:<field>`, the part of the identity the field of
      `Identity` of that name declares, as `identity_table` lays it out
    - For `symbols`, each address `Symbol` declares beside its label, in
      the order of the address
    - For `events`, each flag `Event` declares beside its index, in the
      order the opening sets them
    """
    match name.split(":"):
        case ["settings", subject] : return train.table(f"--{subject}.")
        case ["identity", field]   : return identity_table(field, Identity.read())
        case ["symbols"]:
            return tabulate(
                header = ("Address", "Label"),
                rows = ((f"`0x{symbol:04X}`", f"`{symbol.label}`") for symbol in sorted(
                    Symbol
                ))
            )
        case _:
            return tabulate(
                header = ("Event", "Index"),
                rows   = ((f"`{event.name}`", f"`0x{event:02X}`") for event in Event)
            )
