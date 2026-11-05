"""
Pins what `squirtl cite` does, covering the definition of each key it prints
in the order given, the unknown key and the missing file it refuses with
exit status 1, and the empty call it refuses with exit status 2.
"""

from collections.abc import Callable, Mapping
from common.cli      import Invoker
from pytest          import mark, param

ENTRIES = """
@misc{jones2021, author = {Jones, B.}, title = {U}, year = {2021}, eprint = {2}}
@misc{smith2020, author = {Smith, A.}, title = {T}, year = {2020}, eprint = {1}}
"""


def test_a_citation_prints_each_definition_in_the_order_given(
    checkout : Callable[[Mapping[str, str]], None],
    invoke   : Invoker
):
    """
    Asserts that the command prints each key's definition in the order
    given, a blank line between two, and exits zero.
    """
    checkout({"docs/references.bib": ENTRIES})

    invocation = invoke(["cite", "smith2020", "jones2021"])

    assert (invocation.code, invocation.output) == (
        0,
        '[^smith2020]: Smith 2020. "T." arXiv:1. <https://arxiv.org/abs/1>\n\n'
        '[^jones2021]: Jones 2021. "U." arXiv:2. <https://arxiv.org/abs/2>\n'
    )


@mark.parametrize(
    ("argv", "code", "files"),
    [
        param(
            ["cite", "smith2020", "nobody1999"],
            1,
            {"docs/references.bib": ENTRIES},
            id = "unknown"
        ),
        param(["cite", "smith2020"], 1, {}, id="missing-file"),
        param(
            ["cite", "smith2020"],
            1,
            {"docs/references.bib": "@misc{smith2020, author = {Smith, A.}}"},
            id = "broken-file"
        ),
        param(["cite"], 2, {"docs/references.bib": ENTRIES}, id="no-key")
    ]
)
def test_a_citation_it_cannot_write_exits_nonzero_and_prints_no_definition(
    argv     : list[str],
    code     : int,
    checkout : Callable[[Mapping[str, str]], None],
    files    : Mapping[str, str],
    invoke   : Invoker
):
    """
    Asserts that an unknown key among known ones, a checkout holding no
    `docs/references.bib`, and an entry failing validation each exit 1, and
    that a call naming no key exits 2, each printing no definition.
    """
    checkout(files)

    invocation = invoke(argv)

    assert invocation.code == code
    assert "[^" not in invocation.output
