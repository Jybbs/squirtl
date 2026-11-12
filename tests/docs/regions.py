"""
Pins how `Region` writes each table into a page, covering the pages it
finds, a table written between its pair of markers in place of what the pair
held, the tables of the addresses and the flags, each table of the identity
and a name it does not table, and a marker left unpaired.
"""

from collections.abc    import Callable, Mapping
from importlib.metadata import metadata
from pathlib            import Path
from pytest             import mark, param, raises

from squirtl.cli              import app
from squirtl.docs.commands    import Command
from squirtl.docs.regions     import Region, identity_table, table
from squirtl.identity.schemas import Identity

TRAIN = Command.read(app, ("train",))
"""
The page of `squirtl train`, whose settings each table lists.
"""


def test_a_name_the_identity_tables_no_part_of_fails():
    """
    Pins that a marker naming no part of the identity fails the write by
    name, rather than writing another part's table in its place.
    """
    with raises(ValueError, match="no identity table is named palette"):
        identity_table("palette", IDENTITY)


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


def test_a_pair_of_identity_markers_takes_the_table_of_its_field():
    """
    Asserts that a page's pair of `identity:<field>` markers holds the table
    of that field of the identity once written.
    """
    region = Region(
        path = Path("page.md"),
        text = "<!-- identity:faces -->\n<!-- /identity:faces -->\n"
    )

    assert region.written(TRAIN) == (
        "<!-- identity:faces -->\n\n" + identity_table(
            "faces",
            IDENTITY
        ) + "\n\n<!-- /identity:faces -->\n"
    )


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


IDENTITY = Identity.read()
"""
The identity the package declares, which each identity table reads.
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


@mark.parametrize(
    ("field", "row"),
    [
        param(
            "colors",
            f"| `primary` | Denim | `#3d6fd0` | {IDENTITY.colors['primary'].purpose} |",
            id = "colors"
        ),
        param(
            "neutrals",
            f"| `ground` | Athens Gray | `#f3f4f7` "
            f"| {IDENTITY.neutrals['ground'].purpose} |",
            id = "neutrals"
        ),
        param(
            "ramp",
            "| `deep` | Denim Deep | `#294e95` | 22% black | 7.29:1 | 2.23:1 "
            f"| {IDENTITY.ramp['deep'].purpose} |",
            id = "ramp"
        ),
        param(
            "hues",
            "| Fern | Mirage | Shade 1 | `#1a282c` | 88% Mirage | 1.18:1 |",
            id = "hues"
        ),
        param("order", "| 1 | Denim | `#3d6fd0` | `agent` |", id="order"),
        param("sections", "| Methods | Indigo | `#5d05a4` |", id="sections"),
        param(
            "faces",
            f"| Code | {IDENTITY.faces.code.family} | Code, figures, labels, and chips "
            f"| `{IDENTITY.faces.code.axes}` "
            f"| {', '.join(IDENTITY.faces.code.fallback)} |",
            id = "faces"
        ),
        param(
            "logo",
            "| The dot still ahead | Denim Pale `#92b1e8` | Denim Night `#162d5b` |",
            id = "logo"
        ),
        param("tagline", f"| Byline | {metadata('squirtl')['Summary']} |", id="tagline")
    ]
)
def test_each_identity_table_rows_its_part_of_the_identity(field: str, row: str):
    """
    Pins a row of each table the identity lays out to the figures and the
    names its declaration holds, the contrast each step stands at on its
    ground among them.
    """
    assert row in identity_table(field, IDENTITY).splitlines()


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


def test_the_logo_table_closes_on_the_color_each_game_boy_shade_takes():
    """
    Pins the logo's table to close on the Game Boy's four shades, each
    beside the color of the identity a sprite takes for it.
    """
    assert identity_table("logo", IDENTITY).splitlines()[-4:] == [
        f"| {shade} | {IDENTITY.palette[token].name} `{IDENTITY.palette[token].hex}` |"
        for shade, token in enumerate(IDENTITY.logo.shades)
    ]
