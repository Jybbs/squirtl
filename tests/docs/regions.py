"""
Pins how `Region` writes each subject's table of settings into a page,
covering the pages it finds, a table written between its pair of markers in
place of what the pair held, and a marker left unpaired.
"""

from collections.abc import Callable, Mapping
from pathlib         import Path
from pytest          import mark, param, raises

from squirtl.cli           import app
from squirtl.docs.commands import Command
from squirtl.docs.regions  import Region

TRAIN = Command.read(app, ("train",))
"""
The page of `squirtl train`, whose settings each table lists.
"""


def test_each_pair_takes_its_subjects_table_in_place_of_what_it_held():
    """
    Asserts that each pair of markers holds its subject's table once
    written, whatever it held before, and that the text around each pair
    stays as it was.
    """
    region = Region(
        path = Path("page.md"),
        text = (
            "Before\n<!-- settings:reward -->\nstale\n<!-- /settings:reward -->\n"
            "Between\n<!-- settings:seed -->\n<!-- /settings:seed -->\nAfter\n"
        )
    )

    assert region.written(TRAIN) == (
        "Before\n<!-- settings:reward -->\n\n" + TRAIN.table("--reward.")
        + "\n\n<!-- /settings:reward -->\nBetween\n<!-- settings:seed -->\n\n"
        + TRAIN.table("--seed.") + "\n\n<!-- /settings:seed -->\nAfter\n"
    )


def test_only_a_page_holding_a_marker_is_a_region(
    checkout: Callable[[Mapping[str, str]], None]
):
    """
    Pins that the pages under `docs/pages/` holding a marker are read, in
    the order of their paths, and a page holding none is left out.
    """
    checkout(
        {
            "docs/pages/a/a.md": "<!-- settings:seed -->\n<!-- /settings:seed -->\n",
            "docs/pages/b.md": "<!-- settings:reward -->\n<!-- /settings:reward -->\n",
            "docs/pages/plain.md": "# Plain\n"
        }
    )

    assert [region.path for region in Region.every()] == [
        Path("docs/pages/a/a.md"),
        Path("docs/pages/b.md")
    ]


@mark.parametrize(
    ("text", "line"),
    [
        param(
            "<!-- settings:reward -->\n\n<!-- /settings:agent -->\n",
            3,
            id = "another-subject"
        ),
        param(
            "<!-- /settings:reward -->\n<!-- settings:reward -->\n",
            2,
            id = "closed-first"
        ),
        param("x\n<!-- settings:reward -->\n", 2, id="never-closed"),
        param(
            "<!-- settings:reward -->\n<!-- settings:reward -->\n",
            2,
            id = "opened-twice"
        )
    ]
)
def test_an_unpaired_marker_names_its_page_and_line(text: str, line: int):
    """
    Pins that a marker which is not an opening followed by its own closing
    fails before any table is written, naming the page and the line.
    """
    with raises(SyntaxError, match=f"^page.md:{line}: an unpaired marker$"):
        Region(path=Path("page.md"), text=text).written(TRAIN)
