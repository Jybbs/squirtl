"""
Defines `Inventory`, every file `squirtl write docs` writes into `docs/`
from a declaration in the package, which the `docs:write` task writes
and the `🪧 Audit` row of `🕹️ CI` holds to its declaration, and `Output`,
one of those files, leaving the footnotes of each Markdown file to
`squirtl.docs.schemas`.
"""

from collections.abc import Mapping
from cyclopts        import App
from pathlib         import Path
from pydantic        import TypeAdapter
from typing          import Self

from squirtl.docs.commands       import Command
from squirtl.docs.regions        import Page, Region, Summary
from squirtl.docs.results        import ReleaseSettings, Results
from squirtl.emulator.schemas    import Record, Symbol
from squirtl.environment.schemas import EnvironmentSettings
from squirtl.identity.schemas    import Identity
from squirtl.reward.schemas      import Event
from squirtl.runs.schemas        import RunSettings


class Output(Record):
    """
    One file `squirtl write docs` writes, beside the text its declaration
    gives it.
    """

    path: Path
    """
    The file, relative to the root of the checkout.
    """

    text: str
    """
    What the file holds once written.
    """

    @property
    def drifted(self) -> bool:
        """
        Tells whether the file on disk is missing or holds anything other
        than `text`.
        """
        return not self.path.is_file() or self.path.read_text(
            encoding = "utf-8"
        ) != self.text

    @classmethod
    def from_value(
        cls,
        path    : Path,
        value   : object,
        exclude : Mapping[str, set[str]] | None = None
    ) -> Self:
        """
        Builds the file holding `value` as JSON, two spaces to a level and
        ending on a newline, leaving out each field `exclude` names.
        """
        return cls(
            path = path,
            text = TypeAdapter(type(value)).dump_json(
                value,
                exclude = exclude,
                indent  = 2
            ).decode() + "\n"
        )

    def write(self):
        """
        Writes `text` to the file, making the folder it sits in where it
        is missing.
        """
        self.path.parent.mkdir(exist_ok=True, parents=True)
        self.path.write_text(self.text, encoding="utf-8")


class Inventory(Record):
    """
    Every file `squirtl write docs` writes from a declaration in the
    package, in the order it writes them.
    """

    outputs: tuple[Output, ...]
    """
    The files, each beside the text it holds once written.
    """

    @property
    def drifted(self) -> tuple[Output, ...]:
        """
        Selects the files that are missing or hold anything other than what
        their declaration gives them.
        """
        return tuple(output for output in self.outputs if output.drifted)

    @classmethod
    def read(cls, app: App) -> Self:
        """
        Lists every file the package's declarations are written into, each
        JSON file and the sheet under `docs/.vitepress/lib/rendered/`:

        - The event flags the network reads, in the order the opening sets
          them, each beside its index in the flag array and the term its
          first setting pays toward the default goal, `None` past it
        - The identity's JSON
        - The `@theme` block the site's Tailwind sheet imports
        - The measured runs committed under `docs/runs/`, which the Results
          section draws
        - The settings a release's runs are packed under, which the
          widgets of `squirtl fetch` and `squirtl pack` model
        - The default of every setting a run reads, which the site's widgets
          model, leaving out each field `RunSettings.machine` names
        - The address of every symbol the package reads in the game's memory
        - The parts of the page of each command `app` registers under
          `docs/pages/commands/` written from its help, leaving the prose
          around them
        - Each page under `docs/pages/` carrying the table of a subject's
          settings between a pair of markers
        - The README's sentence on the same runs, where it carries a pair of
          markers
        """
        commands = Command.every(app)
        identity = Identity.read()
        rendered = Path("docs/.vitepress/lib/rendered")
        results  = Results.read()
        terms    = EnvironmentSettings().goal.terms
        train    = next(command for command in commands if command.chain == ("train",))

        return cls(
            outputs = (
                Output.from_value(
                    rendered / "events.json",
                    [
                        {
                            "index" : event.value,
                            "name"  : event.name,
                            "term"  : terms.get(event)
                        }
                        for event in Event
                    ]
                ),
                Output.from_value(rendered / "identity.json", identity),
                Output.from_value(rendered / "results.json", results),
                Output.from_value(rendered / "release.json", ReleaseSettings()),
                Output.from_value(
                    rendered / "settings.json",
                    RunSettings(),
                    exclude = RunSettings.machine
                ),
                Output.from_value(
                    rendered / "symbols.json",
                    {symbol.name: symbol.value for symbol in Symbol}
                ),
                Output(path=rendered / "theme.css", text=identity.sheet),
                *(
                    Output(path=command.path, text=Page.read(command).written(command))
                    for command in commands
                ),
                *(
                    Output(path=region.path, text=region.written(train))
                    for region in Region.every()
                ),
                *(
                    Output(path=summary.path, text=summary.written(train))
                    for summary in Summary.found(results)
                )
            )
        )

    def write(self) -> tuple[Path, ...]:
        """
        Writes each file that has drifted from its declaration, leaving
        every other file untouched.

        Returns:
            The path of each file written, in the order the inventory lists
            them.
        """
        for output in (drifted := self.drifted):
            output.write()

        return tuple(output.path for output in drifted)
