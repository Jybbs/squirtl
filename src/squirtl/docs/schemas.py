"""
Defines the records `squirtl cite` and `squirtl write docs` read:

- `Bibliography`, every source `docs/references.bib` declares, each an `Article`,
  a `Proceedings`, or a `Preprint` writing its own footnote definition
- `Manuscripts`, every Markdown file git tracks, each a `Manuscript` holding
  its footnotes and the text it holds once its definitions are written
"""

from abc          import ABC, abstractmethod
from bibtexparser import parse_string
from bibtexparser.library import Library
from bibtexparser.middlewares import (
    LatexDecodingMiddleware, SeparateCoAuthors, SplitNameParts
)
from bibtexparser.model       import Block, Entry
from collections.abc          import Iterator
from markdown_it              import MarkdownIt
from markdown_it.token        import Token
from mdit_py_plugins.footnote import footnote_plugin
from operator                 import attrgetter
from pathlib import Path
from pydantic            import (
    BeforeValidator, ConfigDict, Field, StringConstraints, ValidationError,
    model_validator
)
from re          import fullmatch, sub
from subprocess  import check_output
from typing      import Annotated, ClassVar, Literal, Self
from unicodedata import normalize

from squirtl.emulator.schemas import Record

type Address = Annotated[str, StringConstraints(pattern=r"^[^\s\\]+$")]


class Source(Record, ABC):
    """
    One entry of `docs/references.bib`, whose kind sets how its definition
    names its venue and links its address, a blank field failing as a
    missing one does and an address failing on any whitespace or backslash
    it holds, since the definition writes an address as the entry holds it.
    """

    model_config = ConfigDict(str_min_length=1, str_strip_whitespace=True)

    authors: Annotated[
        tuple[str, ...],
        BeforeValidator(
            lambda names: [" ".join((*name.von, *name.last)) for name in names]
        ),
        Field(min_length=1, validation_alias="author")
    ]
    """
    Each author's surname, in the order the entry lists them, keeping a
    lowercase particle (`van Hasselt`).
    """

    key: str
    """
    The lowercase surname and year the entry and each marker cite it under.
    """

    title: str
    """
    The title as published.
    """

    year: int
    """
    The year the source was published.
    """

    @property
    @abstractmethod
    def address(self) -> str:
        """
        Writes the address the definition links.
        """

    @property
    def definition(self) -> str:
        """
        Writes the footnote definition, naming one author by surname, two
        joined by `and`, and more as `et al.`
        """
        match self.authors:
            case (only,)         : names = only
            case (first, second) : names = f"{first} and {second}"
            case (first, *_)     : names = f"{first} et al."

        return (
            f'[^{self.key}]: {names} {self.year}. "{self.title}." {self.venue} '
            f"<{self.address}>"
        )

    @property
    @abstractmethod
    def venue(self) -> str:
        """
        Writes where the source appeared, ending on a period.
        """

    @model_validator(mode="after")
    def agrees(self) -> Self:
        """
        Refuses a key other than the first author's surname in lowercase
        ASCII and the year, a letter after the year marking a second source.
        """
        stem = sub(r"[^a-z]", "", normalize("NFKD", self.authors[0]).lower())

        if not fullmatch(rf"{stem}{self.year}[a-z]?", self.key):
            raise ValueError(f"the key disagrees with {stem}{self.year}")

        return self


class Published(Source):
    """
    A source a venue published, linking its DOI, or else the publisher's
    page.
    """

    doi: Address | None = None
    """
    The DOI, where one exists.
    """

    url: Address | None = None
    """
    The publisher's page, for a source with no DOI.
    """

    @property
    def address(self) -> str:
        """
        Writes the DOI's address, or else the publisher's page.
        """
        return f"https://doi.org/{self.doi}" if self.doi else str(self.url)

    @model_validator(mode="after")
    def addressed(self) -> Self:
        """
        Refuses an entry holding neither a DOI nor a publisher's page.
        """
        if not self.doi and not self.url:
            raise ValueError("the entry holds neither a `doi` nor a `url`")

        return self


class Article(Published):
    """
    A journal article.
    """

    journal: str
    """
    The journal's name.
    """

    kind: Literal["article"]
    """
    The BibTeX entry type a journal article takes.
    """

    number: str
    """
    The issue.
    """

    volume: str
    """
    The volume.
    """

    pages: str | None = None
    """
    The page range, for a journal that pages its articles.
    """

    @property
    def venue(self) -> str:
        """
        Writes `*Journal* Volume(Issue): Pages.`, leaving the pages out
        where the entry holds none.
        """
        pages = f": {self.pages}" if self.pages else ""

        return f"*{self.journal}* {self.volume}({self.number}){pages}."


class Proceedings(Published):
    """
    A paper in a conference's proceedings.
    """

    booktitle: str
    """
    The title of the proceedings.
    """

    kind: Literal["inproceedings"]
    """
    The BibTeX entry type a proceedings paper takes.
    """

    pages: str | None = None
    """
    The page range, for proceedings that page their papers.
    """

    series: str | None = None
    """
    The series the proceedings appear in.
    """

    volume: str | None = None
    """
    The volume, for proceedings that number theirs.
    """

    @property
    def venue(self) -> str:
        """
        Writes the proceedings' title, followed by the series, the volume,
        and the pages the entry holds (`*Title*, PMLR 80: 4045–4054.`).
        """
        series = f", {self.series}" if self.series else ""
        volume = f" {self.volume}" if self.volume else ""
        pages  = f": {self.pages}" if self.pages else ""

        return f"*{self.booktitle}*{series}{volume}{pages}."


class Preprint(Source):
    """
    A preprint on arXiv, under its identifier.
    """

    eprint: Address
    """
    The arXiv identifier, carrying a version where a citation rests on one.
    """

    kind: Literal["misc"]
    """
    The BibTeX entry type a preprint takes.
    """

    @property
    def address(self) -> str:
        """
        Writes the address of the preprint's arXiv page.
        """
        return f"https://arxiv.org/abs/{self.eprint}"

    @property
    def venue(self) -> str:
        """
        Writes `arXiv:ID.`
        """
        return f"arXiv:{self.eprint}."


class Fault(Record):
    """
    One way a Markdown file diverges from what `docs:write` writes into it.
    """

    line: int
    """
    The line the divergence sits on, counting from 1.
    """

    message: str
    """
    What diverges, as one sentence.
    """


class Bibliography(Record):
    """
    Every source `docs/references.bib` declares.
    """

    path: ClassVar[Path] = Path("docs/references.bib")

    sources: dict[
        str, Annotated[Article | Proceedings | Preprint, Field(discriminator="kind")]
    ]
    """
    Each source under its key.
    """

    def cite(self, *keys: str) -> tuple[str, ...]:
        """
        Writes the footnote definition of each of `keys`, in the order
        given.

        Raises:
            LookupError: Where a key names no source, naming every such key.
        """
        if unknown := [key for key in keys if key not in self.sources]:
            raise LookupError(
                f"`{self.path}` holds no entry for {', '.join(unknown)}"
            )

        return tuple(self.sources[key].definition for key in keys)

    @classmethod
    def read(cls) -> Self:
        """
        Reads `path` through `bibtexparser`, decoding the LaTeX of every
        field but an address and splitting each author's name into its
        parts.

        Raises:
            SyntaxError: Where a block fails to parse, repeats a key, or
                         holds an entry that fails validation, carrying the
                         line it opens on.
        """
        library = parse_string(
            cls.path.read_text(encoding="utf-8"),
            append_middleware = [
                ProseDecoding(),
                SeparateCoAuthors(),
                SplitNameParts()
            ]
        )

        if failed := library.failed_blocks:
            raise SyntaxError(
                f"The block fails to parse with {failed[0].error!r}",
                (str(cls.path), failed[0].start_line + 1, None, None)
            )

        entries = library.entries_dict

        try:
            return cls(
                sources = {
                    key: {
                        "key"  : key,
                        "kind" : entry.entry_type,
                        **{field.key: field.value for field in entry.fields}
                    }
                    for key, entry in entries.items()
                }
            )
        except ValidationError as error:
            problem       = error.errors()[0]
            _, key, *rest = problem["loc"]

            raise SyntaxError(
                f"`{key}` fails with {' '.join(map(str, (*rest[1:], problem['msg'])))}",
                (str(cls.path), entries[key].start_line + 1, None, None)
            ) from error


class Marker(Record):
    """
    One footnote labeled by a key, where a Markdown file cites or defines
    it.
    """

    key: str
    """
    The label, which has the form every key of the bibliography has.
    """

    line: int
    """
    The line it opens on, counting from 1.
    """

    @property
    def unknown(self) -> str:
        """
        Writes the sentence reporting that the key names no source.
        """
        return f"`[^{self.key}]` names no entry of `{Bibliography.path}`"


class ProseDecoding(LatexDecodingMiddleware):
    """
    Decodes the LaTeX of every field but an address, where `%`, `~`, and `&`
    stand for themselves rather than a comment, a space, and a column.
    """

    addresses: ClassVar[frozenset[str]] = frozenset({"doi", "eprint", "url"})

    def transform_entry(self, entry: Entry, library: Library) -> Block:
        """
        Holds each address aside while the rest of `entry` decodes.
        """
        held = [field for field in entry.fields if field.key in self.addresses]

        entry.fields = [field for field in entry.fields if field not in held]

        try:
            return super().transform_entry(entry, library)
        finally:
            entry.fields = [*entry.fields, *held]


class Definition(Marker):
    """
    One definition of a footnote labeled by a key.
    """

    end: int
    """
    The line after its last, counting from 1, a blank line after the
    definition falling inside it.
    """

    @property
    def lines(self) -> range:
        """
        Spans the lines the definition holds, counting from 1.
        """
        return range(self.line, self.end)


class Manuscript(Record):
    """
    One Markdown file and the footnotes labeled by a key it holds, every
    other footnote standing as part of its text.
    """

    definitions: tuple[Definition, ...]
    """
    Each definition, in the order the file holds them.
    """

    markers: tuple[Marker, ...]
    """
    Each marker outside code, in the order the file cites them.
    """

    path: Path
    """
    The file, relative to the root of the checkout.
    """

    text: str
    """
    What the file holds.
    """

    @property
    def body(self) -> str:
        """
        Writes the text without any definition labeled by a key or the
        newlines ending it.
        """
        lines = self.text.split("\n")

        return "\n".join(lines[number - 1] for number in self.outside).rstrip("\n")

    @property
    def defined(self) -> set[str]:
        """
        Collects the key of each definition the file holds.
        """
        return {definition.key for definition in self.definitions}

    @property
    def firsts(self) -> dict[str, Marker]:
        """
        Selects the first marker of each key, in the order the file first
        cites them.
        """
        firsts = {}

        for marker in self.markers:
            firsts.setdefault(marker.key, marker)

        return firsts

    @property
    def footnoted(self) -> bool:
        """
        Tells whether the file holds a marker or a definition labeled by
        a key.
        """
        return bool(self.markers or self.definitions)

    @property
    def outside(self) -> tuple[int, ...]:
        """
        Numbers each line outside a definition labeled by a key, counting
        from 1.
        """
        written = {line for definition in self.definitions for line in definition.lines}

        return tuple(
            number
            for number in range(1, self.text.count("\n") + 2)
            if number not in written
        )

    @property
    def start(self) -> int:
        """
        Counts the line the first definition opens on once a write closes
        the file on them, counting from 1.
        """
        return self.body.count("\n") + 3

    @property
    def unclosed(self) -> int | None:
        """
        Finds the line opening the block that the text outside each
        definition ends inside, such as a code fence or an HTML comment left
        open, which would hold a definition written after it.

        Returns:
            The line, counting from 1, or `None` where the text ends outside
            every block or the file cites no source, leaving nothing for a
            write to append.
        """
        if not self.markers:
            return None

        start = self.start
        block = next(
            token
            for token in self.parse(f"{self.body}\n\n[^end]: .\n")
            if token.level == 0 and token.map and token.map[0] < start <= token.map[1]
        )

        return (
            None
            if block.type == "footnote_reference_open"
            else self.outside[block.map[0]]
        )

    def citing(self, bibliography: Bibliography) -> Iterator[Fault]:
        """
        Yields a fault at the first marker of each key the bibliography does
        not hold and each key cited with no definition.
        """
        for key, marker in self.firsts.items():
            if key not in bibliography.sources:
                yield Fault(line=marker.line, message=marker.unknown)
            elif key not in self.defined:
                yield Fault(
                    line    = marker.line,
                    message = f"`[^{key}]` has no definition, which `mise write` writes"
                )

    def defining(self, bibliography: Bibliography) -> Iterator[Fault]:
        """
        Yields a fault at each definition no marker cites, differing from
        what its entry writes, or standing anywhere but its place at the end
        of the file, in the order the file first cites each source.
        """
        firsts = self.firsts
        lines  = self.text.split("\n")
        placed = [key for key in firsts if key in self.defined]
        start  = self.start

        for definition in self.definitions:
            key = definition.key

            if key not in firsts:
                yield Fault(
                    line    = definition.line,
                    message = (
                        f"`[^{key}]` is defined and never cited, and `mise write` "
                        "removes it"
                    )
                )
            elif key in bibliography.sources:
                held = "\n".join(lines[definition.line - 1:definition.end - 1])

                if held.rstrip("\n") != bibliography.sources[key].definition:
                    yield Fault(
                        line    = definition.line,
                        message = (
                            f"`[^{key}]` differs from what `{bibliography.path}` "
                            "writes, which `mise write` writes in its place"
                        )
                    )

                if definition.line != start + 2 * placed.index(key):
                    yield Fault(
                        line    = definition.line,
                        message = (
                            f"`[^{key}]` stands outside its place at the end of the "
                            "file, in the order the file first cites each source, "
                            "where `mise write` moves it"
                        )
                    )

    def faults(self, bibliography: Bibliography) -> Iterator[Fault]:
        """
        Yields a fault wherever the file diverges from `written`:

        - A marker of a key the bibliography does not hold, at its first line
        - A key cited with no definition, at its first marker's line
        - A definition no marker cites, one differing from what its entry
          writes, or one standing anywhere but its place at the end of the file
        - A file holding footnotes labeled by a key that ends inside an open
          block, at the line the block opens on, or that ends on anything but
          one newline
        """
        yield from self.citing(bibliography)
        yield from self.defining(bibliography)

        if not self.footnoted:
            return

        if line := self.unclosed:
            yield Fault(
                line    = line,
                message = (
                    "The file ends inside the block opening here, so each definition "
                    "`mise write` appends would fall inside the block, and the write "
                    "refuses the file"
                )
            )

        if self.text != self.text.rstrip("\n") + "\n":
            yield Fault(
                line    = self.text.count("\n") + 1,
                message = "The file ends on something other than one newline"
            )

    @staticmethod
    def keyed(label: str) -> bool:
        """
        Tells whether `label` has the form every key of the bibliography
        has, a footnote under any other label standing as written.
        """
        return fullmatch(r"[a-z]+\d{4}[a-z]?", label) is not None

    @staticmethod
    def parse(text: str) -> list[Token]:
        """
        Parses `text` as CommonMark under the footnote plugin, a marker with
        no definition still parsing as a marker and each definition holding
        its place in the token stream.
        """
        return MarkdownIt("commonmark").use(
            footnote_plugin,
            always_match_refs = True,
            inline            = False,
            move_to_end       = False
        ).parse(text)

    @classmethod
    def read(cls, path: Path) -> Self:
        """
        Reads `path` through `parse`, under which a marker inside code reads
        as code, leaving out a marker inside a definition labeled by a key,
        which a write replaces.

        Raises:
            SyntaxError: Where the file does not decode as UTF-8, naming it.
        """
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            raise SyntaxError(
                f"`{path}` fails to decode with {error}",
                (str(path), None, None, None)
            ) from error

        tokens      = cls.parse(text)
        definitions = tuple(
            Definition(
                end  = token.map[1] + 1,
                key  = token.meta["label"],
                line = token.map[0] + 1
            )
            for token in tokens
            if token.type == "footnote_reference_open"
            and cls.keyed(token.meta["label"])
        )
        written = {line for definition in definitions for line in definition.lines}
        markers = []

        for token in filter(attrgetter("children"), tokens):
            place = 0

            for child in token.children:
                if child.type == "footnote_ref" and cls.keyed(child.meta["label"]):
                    place = token.content.index(f"[^{child.meta['label']}]", place)
                    line  = token.map[0] + 1 + token.content.count("\n", 0, place)

                    if line not in written:
                        markers.append(Marker(key=child.meta["label"], line=line))

                    place += 1

        return cls(
            definitions = definitions,
            markers     = tuple(markers),
            path        = path,
            text        = text
        )

    def written(self, bibliography: Bibliography) -> str:
        """
        Writes what the file holds once each cited source's definition
        closes it, in the order the file first cites them, leaving a file
        with no footnote labeled by a key as it stands.

        Raises:
            LookupError : Where a marker names no source, naming the file
                          and the line.
            SyntaxError : Where the file ends inside an open block, which
                          would hold each definition the write appends,
                          naming the file and the line the block opens on.
        """
        if not self.footnoted:
            return self.text

        for key, marker in self.firsts.items():
            if key not in bibliography.sources:
                raise LookupError(f"{self.path}:{marker.line}: {marker.unknown}")

        if line := self.unclosed:
            raise SyntaxError(
                "The file ends inside the block opening on this line, so each "
                "definition the write appends would fall inside the block",
                (str(self.path), line, None, None)
            )

        return "\n\n".join((self.body, *bibliography.cite(*self.firsts))) + "\n"


class Manuscripts(Record):
    """
    Every Markdown file git tracks.
    """

    files: tuple[Manuscript, ...]
    """
    Each file, in the order git lists them.
    """

    @classmethod
    def read(cls) -> Self:
        """
        Lists the files through `git ls-files`, leaving out one git tracks
        that the working tree no longer holds.
        """
        listing = check_output(
            ["git", "ls-files", "-z", "--", "*.md"],
            encoding = "utf-8"
        )

        return cls(
            files = tuple(
                map(
                    Manuscript.read,
                    filter(Path.is_file, map(Path, listing.split("\0")))
                )
            )
        )

    def write(self, bibliography: Bibliography) -> tuple[Path, ...]:
        """
        Writes each file whose definitions have drifted from `bibliography`,
        once every file's definitions are known to be writable.

        Returns:
            The path of each file written, in the order git lists them.
        """
        changed = {
            file.path: written
            for file in self.files
            if (written := file.written(bibliography)) != file.text
        }

        for path, text in changed.items():
            path.write_text(text, encoding="utf-8")

        return tuple(changed)
