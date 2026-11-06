"""
Pins what the records of `squirtl.docs.schemas` read and write, covering:

- The definition each kind of source writes, and the line each entry a read
  refuses fails at
- The citation of each key, in the order given
- The markers and definitions a Markdown file holds, code and any other label
  left out
- What a file holds once its definitions are written, the faults reported
  against a file differing from that, and the writing of every tracked file
"""

from collections.abc   import Callable, Mapping
from pathlib           import Path
from pytest            import fixture, mark, param, raises
from pytest_subprocess import FakeProcess

from squirtl.docs.schemas import Bibliography, Manuscript, Manuscripts

type Reader = Callable[[str], Bibliography]
type Writer = Callable[[str], Manuscript]
JONES       = '[^jones2021]: Jones 2021. "U." arXiv:2. <https://arxiv.org/abs/2>'
PREPRINT    = {
    "author" : "Smith, A.",
    "eprint" : "1",
    "title"  : "T",
    "year"   : "2020"
}

SMITH = '[^smith2020]: Smith 2020. "T." arXiv:1. <https://arxiv.org/abs/1>'


def entry(key: str, kind: str, **fields: str | None) -> str:
    """
    Writes one entry of a bibliography, each field on a line of its own and
    a blank line after it, leaving out a field set to `None`.
    """
    lines = "".join(
        f"  {name} = {{{value}}},\n" for name, value in fields.items() if value
    )

    return f"@{kind}{{{key},\n{lines}}}\n\n"


@fixture
def read(checkout: Callable[[Mapping[str, str]], None]) -> Reader:
    """
    Builds a reader of a bibliography holding the entries a case names.
    """
    def run(entries: str) -> Bibliography:
        """
        Writes `entries` as `docs/references.bib` and reads it.
        """
        checkout({"docs/references.bib": entries})

        return Bibliography.read()

    return run


@fixture
def bibliography(read: Reader) -> Bibliography:
    """
    Builds a bibliography declaring two preprints.
    """
    return read(
        entry(
            "jones2021",
            "misc",
            **{
                **PREPRINT,
                "author" : "Jones, B.",
                "eprint" : "2",
                "title"  : "U",
                "year"   : "2021"
            }
        )
        + entry("smith2020", "misc", **PREPRINT)
    )


@fixture
def manuscript(checkout: Callable[[Mapping[str, str]], None]) -> Writer:
    """
    Builds a reader of a Markdown file holding the text a case names.
    """
    def run(text: str) -> Manuscript:
        """
        Writes `text` as `a.md` and reads it.
        """
        checkout({"a.md": text})

        return Manuscript.read(Path("a.md"))

    return run


@mark.parametrize(
    ("kind", "key", "fields", "definition"),
    [
        param(
            "article",
            "mnih2015",
            {
                "author"  : "Mnih, V. and Kavukcuoglu, K. and Silver, D.",
                "doi"     : "10.1/n",
                "journal" : "Nature",
                "number"  : "7540",
                "pages"   : "529--533",
                "title"   : "H",
                "volume"  : "518",
                "year"    : "2015"
            },
            '[^mnih2015]: Mnih et al. 2015. "H." *Nature* 518(7540): 529–533. '
            "<https://doi.org/10.1/n>",
            id = "article"
        ),
        param(
            "article",
            "hasselt2016",
            {
                "author"  : "Hasselt, H.",
                "journal" : "J",
                "number"  : "1",
                "title"   : "D",
                "url"     : "https://j.example/d",
                "volume"  : "30",
                "year"    : "2016"
            },
            '[^hasselt2016]: Hasselt 2016. "D." *J* 30(1). <https://j.example/d>',
            id = "article-without-pages"
        ),
        param(
            "inproceedings",
            "pardo2018",
            {
                "author"    : "Pardo, F. and Tavakoli, A.",
                "booktitle" : "P",
                "doi"       : "10.1/p",
                "pages"     : "4045--4054",
                "series"    : "PMLR",
                "title"     : "T",
                "url"       : "https://p.example/t",
                "volume"    : "80",
                "year"      : "2018"
            },
            '[^pardo2018]: Pardo and Tavakoli 2018. "T." *P*, PMLR 80: 4045–4054. '
            "<https://doi.org/10.1/p>",
            id = "proceedings-preferring-the-doi"
        ),
        param(
            "inproceedings",
            "cole2021",
            {
                "author"    : "Cole, A.",
                "booktitle" : "P",
                "pages"     : "1--8",
                "title"     : "T",
                "url"       : "https://p.example/t",
                "volume"    : "34",
                "year"      : "2021"
            },
            '[^cole2021]: Cole 2021. "T." *P* 34: 1–8. <https://p.example/t>',
            id = "proceedings-with-a-volume"
        ),
        param(
            "inproceedings",
            "cole2021",
            {
                "author"    : "Cole, A.",
                "booktitle" : "P",
                "doi"       : "10.1/q",
                "pages"     : "1--8",
                "title"     : "T",
                "year"      : "2021"
            },
            '[^cole2021]: Cole 2021. "T." *P*: 1–8. <https://doi.org/10.1/q>',
            id = "proceedings-with-pages-alone"
        ),
        param(
            "inproceedings",
            "cole2021",
            {
                "author"    : "Cole, A.",
                "booktitle" : "P",
                "doi"       : "10.1/q",
                "title"     : "T",
                "year"      : "2021"
            },
            '[^cole2021]: Cole 2021. "T." *P*. <https://doi.org/10.1/q>',
            id = "proceedings-alone"
        ),
        param(
            "misc",
            "salimans2018",
            {
                "author" : "Salimans, T. and Chen, R.",
                "eprint" : "1812.03381",
                "title"  : "{L}earning",
                "year"   : "2018"
            },
            '[^salimans2018]: Salimans and Chen 2018. "Learning." arXiv:1812.03381. '
            "<https://arxiv.org/abs/1812.03381>",
            id = "preprint"
        ),
        param(
            "misc",
            "vanhasselt2016a",
            {
                "author" : "van Hasselt, H.",
                "eprint" : "1",
                "title"  : "D",
                "year"   : "2016"
            },
            '[^vanhasselt2016a]: van Hasselt 2016. "D." arXiv:1. '
            "<https://arxiv.org/abs/1>",
            id = "particle-and-second-source"
        ),
        param(
            "misc",
            "muller2020",
            {
                "author" : 'M{\\"u}ller, A.',
                "eprint" : "1",
                "title"  : "P{\\'e}",
                "year"   : "2020"
            },
            '[^muller2020]: Müller 2020. "Pé." arXiv:1. <https://arxiv.org/abs/1>',
            id = "latex"
        ),
        param(
            "inproceedings",
            "smith2020",
            {
                "author"    : "Smith, A.",
                "booktitle" : "B",
                "title"     : "T",
                "url"       : "https://a.org/~s/a%20b?x=1&y=2",
                "year"      : "2020"
            },
            '[^smith2020]: Smith 2020. "T." *B*. <https://a.org/~s/a%20b?x=1&y=2>',
            id = "address-holding-latex-marks"
        )
    ]
)
def test_a_source_writes_its_definition(
    definition : str,
    fields     : Mapping[str, str],
    key        : str,
    kind       : str,
    read       : Reader
):
    """
    Pins the definition each kind of source writes, naming its authors by
    the count of them, linking the DOI before the publisher's page, and
    decoding the LaTeX an entry holds.
    """
    assert read(entry(key, kind, **fields)).cite(key) == (definition,)


@mark.parametrize(
    ("entries", "line", "message"),
    [
        param(
            "\n\n" + entry("smith2020", "misc", **{**PREPRINT, "title": None}),
            3,
            "title",
            id = "missing-field"
        ),
        param(
            "@misc{smith2020, author = {Smith, A.}, title = {T}, year = {2020}, "
            "eprint = {}}",
            1,
            "eprint",
            id = "blank-field"
        ),
        param(
            "@misc{smith2020, author = {Smith, A.}, title = {T}, year = {2020}, "
            "eprint = { }}",
            1,
            "eprint",
            id = "whitespace-field"
        ),
        param(
            "@misc{smith2020, author = {}, title = {T}, year = {2020}, eprint = {1}}",
            1,
            "author",
            id = "no-author"
        ),
        param(
            "\n" + entry(
                author  = "Smith, A.",
                journal = "J",
                key     = "smith2020",
                kind    = "article",
                number  = "1",
                title   = "T",
                volume  = "1",
                year    = "2020"
            ),
            2,
            "neither a `doi` nor a `url`",
            id = "missing-address"
        ),
        param(
            entry("jones2020", "misc", **PREPRINT),
            1,
            "smith2020",
            id = "key-disagreeing-on-the-surname"
        ),
        param(
            entry("smith2021", "misc", **PREPRINT),
            1,
            "smith2020",
            id = "key-disagreeing-on-the-year"
        ),
        param(
            entry("smith2020", "misc", **PREPRINT) * 2,
            8,
            "fails to parse",
            id = "duplicate-key"
        ),
        param(
            "\n\n\n@misc{smith2020, author = {Smith, A.",
            4,
            "fails to parse",
            id = "broken-block"
        ),
        param(entry("smith2020", "book", **PREPRINT), 1, "book", id="unknown-kind")
    ]
)
def test_a_bibliography_refuses_an_entry_at_its_line(
    entries : str,
    line    : int,
    message : str,
    read    : Reader
):
    """
    Pins that a missing or blank field, a key disagreeing with its entry, a
    duplicate key, a broken block, and a kind no record takes each fail the
    read at the line the entry opens on.
    """
    with raises(SyntaxError, match=message) as raised:
        read(entries)

    assert (
        raised.value.filename, raised.value.lineno
    ) == (str(Bibliography.path), line)


def test_a_citation_refuses_every_unknown_key(bibliography: Bibliography):
    """
    Pins that a citation writes its definitions in the order given and names
    every key that the bibliography does not declare.
    """
    assert bibliography.cite("smith2020", "jones2021") == (SMITH, JONES)

    with raises(LookupError, match="nobody1999, noone2000"):
        bibliography.cite("nobody1999", "smith2020", "noone2000")


def test_a_manuscript_reads_each_marker_and_definition_at_its_line(manuscript: Writer):
    """
    Pins that a read finds a marker on any line of a paragraph and a
    definition's span, leaving out a marker inside code and any footnote not
    labeled by a key.
    """
    read = manuscript(
        "One\n"
        "two.[^smith2020]\n"
        "\n"
        "`[^code2000]` and[^note] and\\\n"
        "[^jones2021][^smith2020b]\n"
        "\n"
        "```\n"
        "[^fence2000]\n"
        "```\n"
        "\n"
        "[^note]: Stays.\n"
        "\n"
        "[^smith2020]: Written.\n"
    )

    assert [(marker.key, marker.line) for marker in read.markers] == [
        ("smith2020", 2),
        ("jones2021", 5),
        ("smith2020b", 5)
    ]
    assert [
        (definition.key, definition.line, definition.end)
        for definition in read.definitions
    ] == [("smith2020", 13, 14)]


@mark.parametrize(
    ("text", "lines"),
    [
        param("One `a\nb` two\nthree[^smith2020]\n", [3], id="code-span"),
        param(
            'One <span\nclass="a"> two\nthree[^smith2020]\n',
            [3],
            id = "inline-html"
        ),
        param("One[^smith2020]\ntwo[^smith2020]\n", [1, 2], id="repeated-key")
    ]
)
def test_a_manuscript_counts_each_newline_a_paragraph_holds(
    lines      : list[int],
    manuscript : Writer,
    text       : str
):
    """
    Pins a marker's line past a newline that no line break token carries,
    and each repeat of a key at a line of its own.
    """
    assert [marker.line for marker in manuscript(text).markers] == lines


def test_a_manuscript_refuses_a_file_that_does_not_decode_naming_it(tmp_path: Path):
    """
    Pins that a tracked file holding anything but UTF-8 fails its read under
    its own name.
    """
    path = tmp_path / "bad.md"

    path.write_bytes(b"caf\xe9\n")

    with raises(SyntaxError, match=r"bad\.md` fails to decode") as raised:
        Manuscript.read(path)

    assert raised.value.filename == str(path)


@mark.parametrize(
    ("text", "written"),
    [
        param("No footnote,\n\n\n", "No footnote,\n\n\n", id="no-footnote-stands"),
        param(
            f"One.[^smith2020]\n\n[^smith2020]: See [^jones2021].\n",
            f"One.[^smith2020]\n\n{SMITH}\n",
            id = "marker-in-a-definition-stands-out"
        ),
        param(
            "Any.[^note]\n\n[^note]: Stays.\n",
            "Any.[^note]\n\n[^note]: Stays.\n",
            id = "another-label-stands"
        ),
        param(
            "`[^smith2020]`\n",
            "`[^smith2020]`\n",
            id = "marker-in-code-stands"
        ),
        param(
            "One.[^smith2020] Two.[^jones2021] Three.[^smith2020]\n",
            "One.[^smith2020] Two.[^jones2021] Three.[^smith2020]\n\n"
            f"{SMITH}\n\n{JONES}\n",
            id = "first-citation-order"
        ),
        param(
            f"One.[^smith2020]\n\n{JONES}\n\nTwo.[^note]\n\n[^note]: Stays.\n\n"
            "[^smith2020]: Old.\n\n\n",
            f"One.[^smith2020]\n\nTwo.[^note]\n\n[^note]: Stays.\n\n{SMITH}\n",
            id = "moves-replaces-and-removes"
        ),
        param(f"{SMITH}\n", "\n", id="nothing-but-an-uncited-definition")
    ]
)
def test_a_manuscript_writes_each_cited_definition_at_its_end(
    bibliography : Bibliography,
    manuscript   : Writer,
    text         : str,
    written      : str
):
    """
    Pins what a file holds once written, and that writing it again changes
    nothing and reports no fault.
    """
    first = manuscript(text).written(bibliography)
    again = manuscript(first)

    assert first == written
    assert again.written(bibliography) == first
    assert list(again.faults(bibliography)) == []


def test_a_manuscript_refuses_an_unknown_key_at_its_file_and_line(
    bibliography : Bibliography,
    manuscript   : Writer
):
    """
    Pins that a marker of a key the bibliography does not declare fails the
    write, naming the file and the marker's line.
    """
    with raises(LookupError, match=r"a\.md:3: `\[\^nobody1999\]` names no entry"):
        manuscript("One.\n\nTwo.[^nobody1999]\n").written(bibliography)


@mark.parametrize(
    ("text", "faults"),
    [
        param(f"One.[^smith2020]\n\n{SMITH}\n", [], id="clean"),
        param(
            f"One.[^nobody1999] Two.[^smith2020]\n\n[^nobody1999]: X.\n\n{SMITH}\n",
            [(1, "`[^nobody1999]` names no entry of `docs/references.bib`")],
            id = "unknown-holding-its-place"
        ),
        param("One.\n\n\n", [], id="clean-without-a-footnote"),
        param(
            "One.\n\nTwo.[^nobody1999]\n",
            [(3, "`[^nobody1999]` names no entry")],
            id = "unknown"
        ),
        param(
            "One.\n\nTwo.[^smith2020]\n",
            [(3, "`[^smith2020]` has no definition")],
            id = "missing"
        ),
        param(
            f"One.[^smith2020]\n\n{SMITH}\n\n{JONES}\n",
            [(5, "`[^jones2021]` is defined and never cited")],
            id = "uncited"
        ),
        param(
            "One.[^smith2020]\n\n[^smith2020]: By hand.\n",
            [(3, "`[^smith2020]` differs")],
            id = "hand-typed"
        ),
        param(
            f"One.[^smith2020] Two.[^jones2021]\n\n{JONES}\n\n{SMITH}\n",
            [
                (3, "`[^jones2021]` stands outside"),
                (5, "`[^smith2020]` stands outside")
            ],
            id = "out-of-order"
        ),
        param(
            f"One.[^smith2020]\n\n{SMITH}\n\nTwo.\n",
            [(3, "`[^smith2020]` stands outside")],
            id = "before-the-end"
        ),
        param(
            f"One.[^smith2020]\n\n{SMITH}\n\n",
            [(5, "The file ends on something other")],
            id = "extra-newline"
        ),
        param(
            f"One.[^smith2020]\n\n{SMITH}",
            [(3, "The file ends on something other")],
            id = "no-newline"
        ),
        param(
            "One.[^nobody1999]\n\nTwo.[^nobody1999]\n",
            [(1, "`[^nobody1999]` names no entry")],
            id = "unknown-at-its-first-marker"
        ),
        param(
            f"One.[^smith2020]\n\n{SMITH}\n\n    By hand.\n",
            [(3, "`[^smith2020]` differs")],
            id = "hand-typed-continuation"
        ),
        param(
            f"One.[^smith2020] Two.[^jones2021]\n\n{JONES}\n",
            [(1, "`[^smith2020]` has no definition")],
            id = "missing-beside-one-in-its-place"
        )
    ]
)
def test_a_manuscript_reports_each_fault_at_its_line(
    bibliography : Bibliography,
    faults       : list[tuple[int, str]],
    manuscript   : Writer,
    text         : str
):
    """
    Pins each way a file diverges from what a write gives it, and the line
    reporting it.
    """
    found = list(manuscript(text).faults(bibliography))

    assert [fault.line for fault in found] == [line for line, _ in faults]
    assert all(
        fault.message.startswith(message)
        for fault, (_, message) in zip(found, faults, strict=True)
    )


@mark.parametrize(
    "text",
    [
        f"One.[^smith2020]\n\n{SMITH}\n",
        f"One.[^smith2020]  \n  \n\n{SMITH}\n",
        f"One.[^smith2020] Two.[^jones2021]\n\n{SMITH}\n\n{JONES}\n"
    ]
)
def test_a_manuscript_with_no_fault_is_what_a_write_gives(
    bibliography : Bibliography,
    manuscript   : Writer,
    text         : str
):
    """
    Pins that a file reporting no fault is the text a write leaves it
    holding, trailing spaces on its last lines of prose included.
    """
    read = manuscript(text)

    assert (list(read.faults(bibliography)), read.written(bibliography)) == ([], text)


def test_manuscripts_read_each_file_git_lists_that_the_tree_holds(
    checkout : Callable[[Mapping[str, str]], None],
    fp       : FakeProcess
):
    """
    Pins that the read takes the Markdown files git lists, in that order,
    leaving out one the working tree no longer holds.
    """
    checkout({"a.md": "One.\n", "b.md": "Two.\n"})
    fp.register(["git", "ls-files", fp.any()], stdout="b.md\0gone.md\0a.md\0")

    assert [file.path for file in Manuscripts.read().files] == [
        Path("b.md"),
        Path("a.md")
    ]


def test_manuscripts_write_nothing_until_every_file_is_writable(
    bibliography : Bibliography,
    manuscript   : Writer,
    tmp_path     : Path
):
    """
    Pins that a write returns each file it changed and leaves a clean
    file alone, whereas an unknown key in any file leaves every file as
    it stands.
    """
    (tmp_path / "b.md").write_text(f"One.[^smith2020]\n\n{SMITH}\n", encoding="utf-8")
    (tmp_path / "c.md").write_text("One.[^nobody1999]\n", encoding="utf-8")

    pending = manuscript("One.[^jones2021]\n")
    clean   = Manuscript.read(Path("b.md"))
    unknown = Manuscript.read(Path("c.md"))

    with raises(LookupError):
        Manuscripts(files=(pending, unknown)).write(bibliography)

    assert (tmp_path / "a.md").read_text(encoding="utf-8") == "One.[^jones2021]\n"
    assert Manuscripts(files=(pending, clean)).write(bibliography) == (Path("a.md"),)
    assert (tmp_path / "a.md").read_text(
        encoding = "utf-8"
    ) == f"One.[^jones2021]\n\n{JONES}\n"
