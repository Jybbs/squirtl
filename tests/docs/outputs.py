"""
Pins what `Inventory` writes into `docs/`, covering the files it lists, a
file it writes only where the file has drifted from its declaration, and the
folder it makes where a file's folder is missing.
"""

from collections.abc import Callable, Mapping
from json            import loads
from pathlib         import Path
from pytest          import fixture

from squirtl.docs.outputs     import Inventory, Output
from squirtl.identity.schemas import Face, Identity


@fixture
def written() -> dict[str, str]:
    """
    Builds the text each file the inventory lists holds once written, under
    the file's name.
    """
    return {output.path.name: output.text for output in Inventory.read().outputs}


def test_the_events_follow_the_order_the_network_reads_them_in(written: dict[str, str]):
    """
    Pins that the event flags reach the site in the order `Event` declares
    them, which is the order the network reads them in, each beside the term
    the step first setting it pays.
    """
    assert [
        (event["name"], event["term"]) for event in loads(written["events.json"])
    ] == [
        ("EVENT_FOLLOWED_OAK_INTO_LAB", "milestone"),
        ("EVENT_GOT_STARTER", "starter"),
        ("EVENT_OAK_APPEARED_IN_PALLET", "milestone"),
        ("EVENT_OAK_ASKED_TO_CHOOSE_MON", "milestone")
    ]


def test_the_inventory_lists_the_events_the_identity_its_sheet_and_the_settings():
    """
    Pins the files `squirtl write docs` writes, each under
    `docs/.vitepress/lib/rendered/`, the identity's JSON carrying every
    field beside the values the identity derives, which the site reads
    rather than deriving again.
    """
    outputs = {output.path.name: output for output in Inventory.read().outputs}

    assert [*outputs] == [
        "events.json", "identity.json", "settings.json", "theme.css"
    ]
    assert {output.path.parent for output in outputs.values()} == {Path(
        "docs/.vitepress/lib/rendered"
    )}
    identity = loads(outputs["identity.json"].text)

    assert {*identity} == {*Identity.model_fields, *Identity.model_computed_fields}
    assert {*identity["faces"]["body"]} == {
        *Face.model_fields,
        *Face.model_computed_fields
    }


def test_the_settings_leave_out_what_the_machine_chooses(written: dict[str, str]):
    """
    Asserts that the settings the site models carry every subject's defaults
    but the agent's device and the environments an evaluation plays across,
    both of which follow the machine a run starts on, so the file reads the
    same wherever it is written.
    """
    settings = loads(written["settings.json"])

    assert (
        "device" in settings["agent"],
        "environments" in settings["evaluation"],
        settings["evaluation"]["episodes"],
        settings["reward"]["starter"]
    ) == (False, False, 30, 0.6)


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
