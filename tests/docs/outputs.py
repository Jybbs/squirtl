"""
Pins what `Inventory` writes into `docs/`, covering the files it lists, a
file it writes only where the file has drifted from its declaration, the
folder it makes where a file's folder is missing, the prose of a command's
page it keeps, and the modules of `squirtl.docs` loading without the command
line.
"""

from collections.abc import Callable, Mapping
from json            import loads
from pathlib         import Path
from pkgutil         import iter_modules
from pytest          import fixture, mark
from subprocess      import check_output
from sys             import executable

from squirtl               import docs
from squirtl.cli           import app
from squirtl.docs.commands import Command
from squirtl.docs.outputs  import Inventory, Output
from squirtl.emulator.schemas import Symbol
from squirtl.identity.schemas import Face, Identity

PROBE = (
    "from importlib import import_module\n"
    "from sys import argv, modules, set_lazy_imports\n"
    "set_lazy_imports('normal')\n"
    "import_module(argv[1])\n"
    "print('squirtl.cli' in modules)"
)
"""
The program an interpreter of its own runs, importing the module its
argument names with every import loading eagerly, and printing whether
`squirtl.cli` loaded with it.
"""


@fixture
def written() -> dict[str, str]:
    """
    Builds the text each file the inventory lists holds once written, under
    the file's name.
    """
    return {output.path.name: output.text for output in Inventory.read(app).outputs}


def test_a_command_page_keeps_its_prose_once_its_help_is_written_again(
    checkout: Callable[[Mapping[str, str]], None]
):
    """
    Pins that a command's page holding stale help beside prose of its own
    has drifted, and that the inventory writes its help again and keeps
    the prose.
    """
    stop = Command.read(app, ("stop",))
    checkout(
        {
            str(stop.path): (
                "<!-- help -->\nstale\n<!-- /help -->\n\nA point of its own.\n\n"
                "<!-- settings -->\n<!-- /settings -->\n"
            )
        }
    )

    page = next(
        output for output in Inventory.read(app).outputs if output.path == stop.path
    )

    assert page.drifted
    assert page.text == (
        "<!-- help -->\n\n" + stop.parts["help"] + "\n\n<!-- /help -->\n\n"
        "A point of its own.\n\n<!-- settings -->\n\n" + stop.parts["settings"]
        + "\n\n<!-- /settings -->\n"
    )


def test_the_events_follow_the_order_the_network_reads_them_in(written: dict[str, str]):
    """
    Pins that the event flags reach the site in the order `Event` declares
    them, which is the order the network reads them in, each beside its
    index in the flag array and the term the step first setting it pays an
    episode ending at the default goal, `None` past it.
    """
    assert [
        (event["index"], event["name"], event["term"])
        for event in loads(written["events.json"])
    ] == [
        (0x27, "EVENT_OAK_APPEARED_IN_PALLET", "milestone"),
        (0x00, "EVENT_FOLLOWED_OAK_INTO_LAB", "milestone"),
        (0x21, "EVENT_OAK_ASKED_TO_CHOOSE_MON", "milestone"),
        (0x22, "EVENT_GOT_STARTER", "goal"),
        (0x23, "EVENT_BATTLED_RIVAL_IN_OAKS_LAB", None),
        (0x39, "EVENT_GOT_OAKS_PARCEL", None),
        (0x25, "EVENT_GOT_POKEDEX", None)
    ]


def test_the_inventory_lists_the_rendered_files_and_the_pages_it_writes():
    """
    Pins the files `squirtl write docs` writes, the data the site reads
    under `docs/.vitepress/lib/rendered/`, the identity's JSON carrying
    every field beside the values the identity derives, which the site
    reads rather than deriving again, then each command's page under
    `docs/pages/commands/`, then each page holding a table of settings, then
    the README holding its sentence on the results.
    """
    *listed, readme = Inventory.read(app).outputs
    outputs         = {output.path.as_posix(): output for output in listed}
    pages           = [path for path in outputs if path.startswith("docs/pages/")]

    assert readme.path == Path(".github/README.md")
    assert [Path(path).name for path in outputs if path not in pages] == [
        "events.json", "identity.json", "results.json", "release.json",
        "settings.json", "symbols.json", "theme.css"
    ]
    assert {Path(path).parent for path in outputs if path not in pages} == {Path(
        "docs/.vitepress/lib/rendered"
    )}
    assert [path for path in pages if path.startswith("docs/pages/commands/")] == [
        f"docs/pages/commands/{name}.md"
        for name in (
            "cite", "evaluate", "fetch", "pack", "search",
            "stop", "train", "watch", "write-docs"
        )
    ]
    assert "docs/pages/methods/reward.md" in pages
    identity = loads(outputs["docs/.vitepress/lib/rendered/identity.json"].text)

    assert {*identity} == {*Identity.model_fields, *Identity.model_computed_fields}
    assert {*identity["faces"]["body"]} == {
        *Face.model_fields,
        *Face.model_computed_fields
    }


def test_the_settings_leave_out_what_the_machine_chooses(written: dict[str, str]):
    """
    Asserts that the settings the site models carry every subject's defaults
    but the agent's device, the environments an evaluation plays across, and
    the workers a search runs across, each of which follows the machine a
    run starts on, so the file reads the same wherever it is written.
    """
    settings = loads(written["settings.json"])

    assert (
        "device" in settings["agent"],
        "environments" in settings["evaluation"],
        "workers" in settings["search"],
        settings["evaluation"]["episodes"],
        settings["reward"]["goal"],
        settings["environment"]["goal"],
        settings["search"]["particles"]
    ) == (False, False, False, 30, 0.35, "EVENT_GOT_STARTER", 32)


def test_the_symbols_reach_the_site_at_their_addresses(written: dict[str, str]):
    """
    Pins that every address `Symbol` declares reaches the site under its
    name, so a widget reading the game's memory reads the package's own.
    """
    assert loads(written["symbols.json"]) == {
        symbol.name: symbol.value for symbol in Symbol
    }


def test_writing_touches_only_the_files_that_drifted(
    checkout: Callable[[Mapping[str, str]], None]
):
    """
    Pins that the inventory writes a missing file and a changed one, making
    the missing file's folder, leaves a current file as it was, and returns
    the paths it wrote in the order it lists them.
    """
    checkout({"changed.txt": "old\n", "current.txt": "kept\n"})
    current = Output(path=Path("current.txt"), text="kept\n")
    changed = Output(path=Path("changed.txt"), text="new\n")
    missing = Output(path=Path("deep/missing.txt"), text="made\n")

    inventory = Inventory(outputs=(changed, current, missing))

    assert [output.path for output in inventory.drifted] == [changed.path, missing.path]
    assert inventory.write() == (changed.path, missing.path)
    assert (
        inventory.drifted,
        missing.path.read_text(encoding="utf-8")
    ) == ((), "made\n")


@mark.parametrize(
    "module",
    [
        docs.__name__,
        *(module.name for module in iter_modules(docs.__path__, f"{docs.__name__}."))
    ]
)
def test_squirtl_docs_and_each_of_its_modules_load_without_the_command_line(
    module: str
):
    """
    Asserts that importing `squirtl.docs` or one of its modules, in an
    interpreter of its own whose imports all load eagerly so an import of
    the command line runs where it is written, leaves `squirtl.cli` out
    of `sys.modules`.
    """
    assert check_output([executable, "-c", PROBE, module], text=True) == "False\n"
