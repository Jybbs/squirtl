"""
Pins how `Region` writes each table into a page, covering the pages it
finds, a table written between its pair of markers in place of what the pair
held, the tables of the addresses and the flags, and a marker left unpaired.
"""

from collections.abc import Callable, Mapping
from pathlib         import Path
from pytest          import mark, param, raises

from squirtl.cli           import app
from squirtl.docs.commands import Command
from squirtl.docs.regions  import Region, table

TRAIN = Command.read(app, ("train",))
"""
The page of `squirtl train`, whose settings each table lists.
"""


def test_a_pair_of_symbols_markers_takes_the_table_of_the_addresses():
    """
    Asserts that a page's pair of `symbols` markers holds the table of the
    addresses once written.
    """
    region = Region(path=Path("page.md"), text="<!-- symbols -->\n<!-- /symbols -->\n")

    assert region.written(TRAIN) == (
        "<!-- symbols -->\n\n" + table("symbols", TRAIN) + "\n\n<!-- /symbols -->\n"
    )


@mark.parametrize(
    ("name", "rows"),
    [
        param(
            "symbols",
            [
                "| `0xD35E` | `wCurMap` |", "| `0xD361` | `wYCoord` |",
                "| `0xD362` | `wXCoord` |", "| `0xD747` | `wEventFlags` |"
            ],
            id = "symbols"
        ),
        param(
            "events",
            [
                "| `EVENT_FOLLOWED_OAK_INTO_LAB` | `0x00` | `--reward.milestone` |",
                "| `EVENT_OAK_ASKED_TO_CHOOSE_MON` | `0x21` | `--reward.milestone` |",
                "| `EVENT_GOT_STARTER` | `0x22` | `--reward.starter` |",
                "| `EVENT_OAK_APPEARED_IN_PALLET` | `0x27` | `--reward.milestone` |"
            ],
            id = "events"
        )
    ]
)
def test_the_addresses_and_the_flags_are_tabled_in_the_order_of_their_values(
    name : str,
    rows : list[str]
):
    """
    Pins the rows of the table of the addresses `Symbol` declares, each
    beside its label, and of the flags `Event` declares, each beside its
    index and the setting holding what it pays.
    """
    assert table(name, TRAIN).splitlines()[2:] == rows


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
            "docs/pages/a/a.md"   : "<!-- settings:seed -->\n<!-- /settings:seed -->\n",
            "docs/pages/b.md"     : "<!-- events -->\n<!-- /events -->\n",
            "docs/pages/plain.md" : "# Plain\n"
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
        param(
            "<!-- /settings:reward -->\n<!-- /settings:reward -->\n",
            2,
            id = "closed-twice"
        ),
        param("<!-- symbols -->\n<!-- /events -->\n", 2, id="another-table"),
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
