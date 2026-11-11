"""
Pins the pages `Command` writes for the commands `squirtl`
registers, covering:

- The commands it finds, each word of a group's command after the group's
- A page's heading, help without the `Args` section, and usage, beside its
  table of settings, which leaves out a setting the help hides
- How a setting spells its flag and its default, whether the default
  follows the machine, no default exists, or the default is a boolean, an
  enumeration, a pair, `None`, or a number
- A paragraph's lines joined into one, a list keeping its items
"""

from cyclopts import App, Parameter
from enum     import StrEnum
from pytest   import mark, param
from typing   import Annotated

from squirtl.cli            import app
from squirtl.docs.commands  import Command, spelled, unwrapped
from squirtl.reward.schemas import Event


class Shade(StrEnum):
    """
    A choice a stand-in command takes, spelled by the name cyclopts gives
    its member.
    """

    LIGHT = "light"


def test_a_command_taking_no_setting_carries_no_table():
    """
    Pins that a command with no setting of its own leaves out the part its
    page would otherwise close on, the heading and the table of settings.
    """
    stand_in = App(name="stand-in")

    @stand_in.command
    def bare():
        """
        Does nothing.
        """

    assert list(Command.read(stand_in, ("bare",)).parts) == ["help"]


def test_a_default_following_the_machine_is_named_so():
    """
    Pins that the agent's device and the environments an evaluation plays
    across, which `RunSettings.machine` names, read as the machine's rather
    than as the value the machine writing the page holds.
    """
    rows = Command.read(app, ("train",)).table("--agent.device")

    assert "| `--agent.device` | *the machine's* |" in rows


def test_a_hidden_setting_takes_no_row():
    """
    Asserts that a setting cyclopts hides from the help is left out of the
    page's table while the setting beside it is kept.
    """
    stand_in = App(name="stand-in")

    @stand_in.command
    def paint(secret: Annotated[int, Parameter(show=False)] = 0, shade: Shade = Shade.LIGHT):
        """
        Paints.

        Args:
            shade: The shade to paint in.
        """

    settings = Command.read(stand_in, ("paint",)).settings

    assert [setting.name for setting in settings] == ["--shade"]


def test_a_page_carries_the_description_without_the_args_section():
    """
    Asserts that a page's help holds the summary and each paragraph after it
    while the docstring's `Args` section reaches only the table.
    """
    stand_in = App(name="stand-in")

    @stand_in.command
    def paint(shade: Shade = Shade.LIGHT):
        """
        Paints the wall in one coat.

        Covers the trim too.

        Args:
            shade: The shade to paint in.
        """

    assert Command.read(stand_in, ("paint",)).help == (
        "Paints the wall in one coat.\n\nCovers the trim too."
    )


def test_a_page_lays_out_its_heading_help_usage_and_settings():
    """
    Asserts that the help part of the page of `squirtl stop` opens on its
    name as code and closes on its usage in a console block, and that its
    settings part tables its positional setting named both ways and spelled
    as required, whereas the page of `squirtl watch` tables an optional one
    under its default.
    """
    parts = Command.read(app, ("stop",)).parts

    assert parts["help"].startswith("# `squirtl stop`\n\nWrites the stop file")
    assert parts["help"].endswith("```console\nsquirtl stop DIRECTORY\n```")
    assert parts["settings"].startswith("## Settings\n\n| **Flag** |")
    assert "| `DIRECTORY`, `--directory` | *required* |" in parts["settings"]
    assert "| `--episode` | `none` |" in Command.read(app, ("watch",)).parts["settings"]


def test_a_paragraph_joins_its_lines_and_keeps_each_item_of_a_list():
    """
    Pins that the lines of one paragraph join with spaces while each item of
    a list stays on a line of its own.
    """
    assert unwrapped("Each of\n  these exits:\n- One\n- Two\n  more\n") == (
        "Each of these exits:\n- One\n- Two more"
    )


def test_a_stand_in_setting_spells_its_enumeration_default():
    """
    Asserts that a setting taking an enumeration tables its default by the
    name cyclopts gives the member.
    """
    stand_in = App(name="stand-in")

    @stand_in.command
    def paint(shade: Shade = Shade.LIGHT):
        """
        Paints.

        Args:
            shade: The shade to paint in.
        """

    assert "| `SHADE`, `--shade` | `light` | *The shade to paint in.* |" in (
        Command.read(stand_in, ("paint",)).parts["settings"]
    )


@mark.parametrize(
    ("value", "spelling"),
    [
        param(None, "none", id="none"),
        param(True, "true", id="boolean"),
        param(Shade.LIGHT, "light", id="enumeration"),
        param(Event.EVENT_GOT_STARTER, "event-got-starter", id="integer-enumeration"),
        param((72, 80), "72, 80", id="pair"),
        param(0.25, "0.25", id="number")
    ]
)
def test_each_default_is_spelled_as_the_flag_takes_it(value: object, spelling: str):
    """
    Pins how each kind of default is spelled on a page, matching what the
    flag reads back.
    """
    assert spelled(value) == spelling


def test_a_table_holds_only_the_settings_under_its_prefix():
    """
    Asserts that the table of one subject's settings holds each of its flags
    and no other subject's.
    """
    rows = (
        Command.read(app, ("train",))
               .table("--reward.")
               .splitlines()
    )[2:]

    assert [row.split(" | ")[0] for row in rows] == [
        "| `--reward.goal`", "| `--reward.milestone`", "| `--reward.novelty`"
    ]


def test_every_command_the_package_registers_takes_a_page():
    """
    Pins that each command `squirtl` registers takes a page named for the
    words after `squirtl`, a group's command after the group's name, in
    alphabetical order of those words, with no page for the help and version
    flags.
    """
    assert [command.path.name for command in Command.every(app)] == [
        "cite.md", "evaluate.md", "fetch.md", "pack.md",
        "stop.md", "train.md", "watch.md", "write-docs.md"
    ]
