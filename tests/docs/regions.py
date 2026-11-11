"""
Pins how `Region` writes each table into a page, covering the pages it
finds, a table written between its pair of markers in place of what the
pair held, the tables of the addresses and the flags, and a marker left
unpaired, how `Page` writes the parts of a command's page around its own
prose, covering a page not yet written and markers naming other parts, and
how `Summary` writes the README's sentence on the results, covering a README
holding no marker.
"""

from collections.abc import Callable, Mapping
from pathlib         import Path
from pytest          import mark, param, raises

from squirtl.cli           import app
from squirtl.docs.commands import Command
from squirtl.docs.regions  import Page, Region, Summary, table
from squirtl.docs.results  import Results

STOP = Command.read(app, ("stop",))
"""
The parts of the page of `squirtl stop`, a command taking a setting.
"""

TRAIN = Command.read(app, ("train",))
"""
The page of `squirtl train`, whose settings each table lists.
"""


def test_a_page_keeps_its_prose_and_rewrites_each_part(
    checkout: Callable[[Mapping[str, str]], None]
):
    """
    Asserts that rewriting a command's page puts each part of its command in
    place of what its pair of markers held while the prose before, between,
    and after the pairs stays as it was.
    """
    checkout(
        {
            "docs/pages/commands/stop.md": (
                "Above\n<!-- help -->\nstale\n<!-- /help -->\n\nBetween\n\n"
                "<!-- settings -->\n<!-- /settings -->\nBelow\n"
            )
        }
    )

    assert Page.read(STOP).written(STOP) == (
        "Above\n<!-- help -->\n\n" + STOP.parts["help"]
        + "\n\n<!-- /help -->\n\nBetween\n\n<!-- settings -->\n\n"
        + STOP.parts["settings"] + "\n\n<!-- /settings -->\nBelow\n"
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
                "| `EVENT_OAK_APPEARED_IN_PALLET` | `0x27` |",
                "| `EVENT_FOLLOWED_OAK_INTO_LAB` | `0x00` |",
                "| `EVENT_OAK_ASKED_TO_CHOOSE_MON` | `0x21` |",
                "| `EVENT_GOT_STARTER` | `0x22` |",
                "| `EVENT_BATTLED_RIVAL_IN_OAKS_LAB` | `0x23` |",
                "| `EVENT_GOT_OAKS_PARCEL` | `0x39` |",
                "| `EVENT_GOT_POKEDEX` | `0x25` |"
            ],
            id = "events"
        )
    ]
)
def test_the_addresses_and_the_flags_are_tabled_in_their_order(
    name : str,
    rows : list[str]
):
    """
    Pins the rows of the table of the addresses `Symbol` declares, each
    beside its label in the order of the address, and of the flags `Event`
    declares, each beside its index in the order the opening sets them.
    """
    assert table(name, TRAIN).splitlines()[2:] == rows


def test_a_page_not_yet_written_holds_each_part_of_its_command(
    checkout: Callable[[Mapping[str, str]], None]
):
    """
    Pins that the page of a command with no file yet holds the help part and
    then the settings part, each between its pair of markers, and no prose.
    """
    checkout({})

    assert Page.read(STOP).written(STOP) == (
        "<!-- help -->\n\n" + STOP.parts["help"] + "\n\n<!-- /help -->\n\n"
        "<!-- settings -->\n\n" + STOP.parts["settings"]
        + "\n\n<!-- /settings -->\n"
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
    with raises(SyntaxError, match=r"^`page\.md` holds an unpaired marker") as raised:
        Region(path=Path("page.md"), text=text).written(TRAIN)

    assert (raised.value.filename, raised.value.lineno) == ("page.md", line)


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
    ("text", "names", "line"),
    [
        param("# `squirtl stop`\n", "nothing", None, id="no-markers"),
        param("x\n<!-- help -->\n<!-- /help -->\n", "help", 2, id="settings-missing"),
        param(
            "<!-- settings -->\n<!-- /settings -->\n<!-- help -->\n<!-- /help -->\n",
            "settings, help",
            1,
            id = "out-of-order"
        ),
        param(
            "<!-- help -->\n<!-- /help -->\n<!-- help -->\n<!-- /help -->\n"
            "<!-- settings -->\n<!-- /settings -->\n",
            "help, help, settings",
            1,
            id = "repeated"
        )
    ]
)
def test_a_page_whose_markers_name_other_parts_is_refused(
    line  : int | None,
    names : str,
    text  : str
):
    """
    Pins that a command's page whose pairs of markers do not name the parts
    of its command in order, each once, fails before any part is written,
    naming the page, the pairs it holds, and the line of its first marker.
    """
    with raises(
        SyntaxError,
        match = f"^`page.md` holds markers naming {names} rather than help, settings"
    ) as raised:
        Page(path=Path("page.md"), text=text).written(STOP)

    assert (raised.value.filename, raised.value.lineno) == ("page.md", line)


@mark.parametrize(
    "files",
    [
        param({}, id="missing"),
        param({".github/README.md": "# SquiRtL\n"}, id="no-markers")
    ]
)
def test_a_readme_holding_no_marker_holds_no_summary(
    checkout : Callable[[Mapping[str, str]], None],
    files    : Mapping[str, str]
):
    """
    Pins that a checkout whose README is missing or holds no marker yields
    no summary to write.
    """
    checkout(files)

    assert [*Summary.found(Results.read())] == []


def test_the_summary_links_the_results_before_its_sentence(
    checkout: Callable[[Mapping[str, str]], None]
):
    """
    Pins that the README's pair of markers holds the link to the site's
    Results section at the package's `Homepage` before the sentence on the
    results, whatever it held before, the prose around it kept.
    """
    checkout(
        {
            ".github/README.md":
                "# SquiRtL\n\n<!-- results -->\nstale\n<!-- /results -->\n"
        }
    )
    results   = Results.read()
    [summary] = Summary.found(results)

    assert summary.written(TRAIN) == (
        "# SquiRtL\n\n<!-- results -->\n\n**[Results](https://squirtl.fyi/results/)** "
        f"{results.summary}\n\n<!-- /results -->\n"
    )
