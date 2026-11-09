"""
Pins what `squirtl write docs` does, covering the files it writes into a
checkout missing them, the definitions it closes each tracked Markdown file
on, the path of each it prints, a second run printing nothing once every
file matches its declaration, the unknown key that fails before any file
is written, and the unpaired marker that fails before any file but the
footnotes is written.
"""

from collections.abc   import Callable, Mapping
from common.cli        import Invoker
from pathlib           import Path
from pytest            import mark, param
from pytest_subprocess import FakeProcess
from subprocess        import run

from squirtl.docs.outputs import Inventory

ENTRY = """
    @misc{
        smith2020,
        author = {Smith, A.},
        title  = {T},
        year   = {2020},
        eprint = {1}
    }
"""


def test_writing_docs_over_an_unpaired_marker_exits_1_and_writes_nothing_else(
    checkout : Callable[[Mapping[str, str]], None],
    clone    : Path,
    invoke   : Invoker
):
    """
    Asserts that a page under `docs/pages/` holding an unpaired marker exits
    1 without a traceback and leaves every other file the inventory lists
    unwritten.
    """
    checkout(
        {
            "docs/pages/page.md"  : "<!-- settings:reward -->\n",
            "docs/references.bib" : ENTRY
        }
    )

    invocation = invoke(["write", "docs"])

    assert (invocation.code, invocation.output, invocation.messages) == (
        1, "",
        ["docs/pages/page.md:1: an unpaired marker"]
    )
    assert not (clone / "docs/.vitepress/lib/rendered/identity.json").exists()


@mark.parametrize(
    "files",
    [
        param(
            {"a.md": "One.[^nobody1999]\n", "docs/references.bib": ENTRY},
            id = "unknown-key"
        ),
        param({"a.md": "One.\n"}, id="missing-bibliography"),
        param(
            {
                "a.md"                : "One.\n",
                "docs/references.bib" : "@misc{smith2020, author = {Smith, A.}}"
            },
            id = "broken-bibliography"
        )
    ]
)
def test_writing_docs_it_cannot_write_exits_1_and_writes_nothing(
    checkout : Callable[[Mapping[str, str]], None],
    clone    : Path,
    files    : Mapping[str, str],
    invoke   : Invoker
):
    """
    Asserts that an unknown key, a missing `docs/references.bib`, and an
    entry failing validation each exit 1 and leave the Markdown file and the
    inventory's files unwritten.
    """
    checkout(files)
    run(["git", "add", "a.md"], check=True, cwd=clone)

    invocation = invoke(["write", "docs"])

    assert (invocation.code, invocation.output) == (1, "")
    assert (clone / "a.md").read_text(encoding="utf-8") == files["a.md"]
    assert not any(output.path.exists() for output in Inventory.read().outputs)


def test_writing_docs_where_git_fails_exits_1_and_writes_nothing(
    checkout : Callable[[Mapping[str, str]], None],
    fp       : FakeProcess,
    invoke   : Invoker
):
    """
    Asserts that a `git ls-files` exiting nonzero exits 1 and leaves the
    inventory's files unwritten.
    """
    checkout({"docs/references.bib": ENTRY})
    fp.register(["git", "ls-files", "-z", "--", "*.md"], returncode=128)

    invocation = invoke(["write", "docs"])

    assert (invocation.code, invocation.output) == (1, "")
    assert not any(output.path.exists() for output in Inventory.read().outputs)


def test_writing_docs_writes_each_file_once_and_prints_its_path(
    checkout : Callable[[Mapping[str, str]], None],
    clone    : Path,
    invoke   : Invoker
):
    """
    Asserts that the command closes a tracked Markdown file on its
    definition and writes every file the inventory lists into a checkout
    holding none of them, printing each path, and that a second run finds
    nothing drifted and prints nothing.
    """
    checkout({"a.md": "One.[^smith2020]\n", "docs/references.bib": ENTRY})
    run(["git", "add", "a.md"], check=True, cwd=clone)

    paths  = ["a.md", *(str(output.path) for output in Inventory.read().outputs)]
    first  = invoke(["write", "docs"])
    second = invoke(["write", "docs"])

    assert (first.code, first.output.splitlines()) == (0, paths)
    assert (second.code, second.output) == (0, "")
    assert (clone / "a.md").read_text(encoding="utf-8") == (
        'One.[^smith2020]\n\n[^smith2020]: Smith 2020. "T." arXiv:1. '
        "<https://arxiv.org/abs/1>\n"
    )
