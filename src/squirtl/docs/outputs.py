"""
Defines `Inventory`, every file `squirtl write docs` writes into `docs/`
from a declaration in the package, which the `docs:write` task writes and
the `🗺️ Audit` row of `🕹️ CI` holds to its declaration, and `Output`, one of
those files.
"""

from collections.abc import Mapping
from pathlib         import Path
from pydantic        import TypeAdapter
from typing          import Self

from squirtl.emulator.schemas import Record
from squirtl.identity.schemas import Identity
from squirtl.reward.schemas   import Event
from squirtl.runs.schemas     import RunSettings


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
    Every file `squirtl write docs` writes, in the order it writes them.
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
    def read(cls) -> Self:
        """
        Lists every file the package's declarations are written into under
        `docs/.vitepress/lib/rendered/`:

        - The event flags the network reads, in their order, each beside the
          term it pays
        - The identity's JSON
        - The `@theme` block the site's Tailwind sheet imports
        - The default of every setting a run reads, which the site's widgets
          model, leaving out the agent's device and the environments an
          evaluation plays across, both of which follow the machine a run
          starts on
        """
        identity = Identity.read()
        rendered = Path("docs/.vitepress/lib/rendered")

        return cls(
            outputs = (
                Output.from_value(
                    rendered / "events.json",
                    [{"name": event.name, "term": event.term} for event in Event]
                ),
                Output.from_value(rendered / "identity.json", identity),
                Output.from_value(
                    rendered / "settings.json",
                    RunSettings(),
                    exclude = {"agent": {"device"}, "evaluation": {"environments"}}
                ),
                Output(path=rendered / "theme.css", text=identity.sheet)
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
