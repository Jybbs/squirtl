"""
Defines `Command`, the parts of the page of the site's Commands section
that `squirtl write docs` writes for each command the `squirtl` command
registers, from the help cyclopts prints for it, and `Setting`, one row of
the table of settings that page carries.
"""

from collections.abc import Iterator
from cyclopts        import App, Argument, default_name_transform
from cyclopts.help   import format_doc, format_usage
from enum            import Enum
from functools       import reduce
from inspect         import Parameter
from operator        import getitem
from pathlib         import Path
from re              import sub
from typing          import Self

from squirtl.emulator.schemas import Record
from squirtl.markdown.tables  import tabulate
from squirtl.runs.settings    import RunSettings


class Setting(Record):
    """
    One setting a command takes, as the row of its page's table naming the
    flag, its default, and what it sets.
    """

    default: str
    """
    The default the flag takes, spelled for the page.
    """

    flag: str
    """
    The flag, beside the name its value takes where it also fills a
    position.
    """

    help: str
    """
    What the setting sets, as one paragraph.
    """

    name: str
    """
    The flag alone, such as `--agent.discount`.
    """

    @property
    def row(self) -> tuple[str, str, str]:
        """
        Spells the cells of the setting's row in the page's Markdown table,
        the flag, the default, and what it sets in italics.
        """
        return self.flag, self.default, f"*{self.help}*"

    @classmethod
    def read(cls, argument: Argument) -> Self:
        """
        Builds the row of `argument`, one entry of the `ArgumentCollection`
        cyclopts assembles for a command, spelling a default that follows
        the machine a run starts on as that, and one no flag needs as
        required.
        """
        subject, _, field = (
            argument.name.removeprefix("--")
                    .replace("-", "_")
                    .partition(".")
        )
        default = argument.field_info.default
        flag    = f"`{argument.name}`"

        return cls(
            default = (
                "*the machine's*" if field in RunSettings.machine.get(subject, ())
                else "*required*" if default is Parameter.empty
                else f"`{spelled(default)}`"
            ),
            flag = flag if argument.index is None else
                f"`{argument.name.removeprefix('--').upper()}`, {flag}",
            help = unwrapped(argument.parameter.help),
            name = argument.name
        )


class Command(Record):
    """
    The parts of the page of one command the `squirtl` command registers,
    written from the help cyclopts prints for it.
    """

    chain: tuple[str, ...]
    """
    The words naming the command after `squirtl`, such as `write docs`.
    """

    help: str
    """
    The description cyclopts prints above the command's usage, one
    paragraph to a blank line, without the docstring's `Args` section.
    """

    settings: tuple[Setting, ...]
    """
    Each setting the command takes, in the order its help lists them.
    """

    usage: str
    """
    The usage line cyclopts prints for the command.
    """

    @property
    def parts(self) -> dict[str, str]:
        """
        Lays out each part of the page written from the command, by the name
        of the pair of markers holding it:

        - `help`, the heading, the command's help, and its usage
        - `settings`, the heading and the table of every setting it takes,
          where it takes any
        """
        return {
            "help": "\n".join(
                [
                    f"# `squirtl {' '.join(self.chain)}`",
                    "", self.help, "", "```console", self.usage, "```"
                ]
            ),
            **({"settings": "## Settings\n\n" + self.table()} if self.settings else {})
        }

    @property
    def path(self) -> Path:
        """
        Locates the page under `docs/pages/commands/`, named for the words
        after `squirtl` joined by hyphens.
        """
        return Path("docs/pages/commands", "-".join(self.chain) + ".md")

    @classmethod
    def every(cls, app: App) -> tuple[Self, ...]:
        """
        Builds the page of every command `app` registers, a group's commands
        in place of the group, in alphabetical order of the words naming
        each.
        """
        return tuple(
            sorted(
                (cls.read(app, chain) for chain in commands(app)),
                key = lambda command: command.chain
            )
        )

    @classmethod
    def read(cls, app: App, chain: tuple[str, ...]) -> Self:
        """
        Builds the page of the command of `app` that `chain` names, from the
        help cyclopts prints for it.
        """
        command = reduce(getitem, chain, app)

        return cls(
            chain = chain,
            help  = "\n\n".join(
                unwrapped(paragraph)
                for paragraph in format_doc(command, "plaintext")
                    .primary_renderable.plain
                    .split("\n\n")
            ),
            settings = tuple(
                Setting.read(argument)
                for argument in command.assemble_argument_collection(
                    parse_docstring = True
                )
                if argument.show and not argument.children
            ),
            usage = str(format_usage(app, chain)).strip()
        )

    def table(self, prefix: str = "") -> str:
        """
        Lays out the Markdown table of each setting whose flag opens on
        `prefix`, every setting where `prefix` is empty.
        """
        return tabulate(
            header = ("Flag", "Default", "What It Sets"),
            rows   = (
                setting.row
                for setting in self.settings
                if setting.name.startswith(prefix)
            )
        )


def commands(app: App, chain: tuple[str, ...] = ()) -> Iterator[tuple[str, ...]]:
    """
    Yields the words naming each command `app` registers, descending into
    each group in place of naming it, and leaving out the help and version
    flags cyclopts registers as commands.
    """
    for name in app:
        if name.startswith("-"):
            continue

        if (command := app[name]).default_command is None:
            yield from commands(command, (*chain, name))
        else:
            yield (*chain, name)


def spelled(value: object) -> str:
    """
    Spells a default as the flag takes it, a boolean in lowercase, an
    enumeration by the name cyclopts gives its member, a pair by its members
    split by a comma, and `None` as `none`.
    """
    match value:
        case None    : return "none"
        case bool()  : return str(value).lower()
        case Enum()  : return default_name_transform(value.name)
        case tuple() : return ", ".join(map(spelled, value))
        case _       : return str(value)


def unwrapped(text: str) -> str:
    """
    Joins the lines of one paragraph of a docstring with spaces, keeping
    each item of a list on a line of its own.
    """
    return sub(r"\s*\n(?!- )\s*", " ", text.strip())
