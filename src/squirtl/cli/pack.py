"""
Defines `pack`, the command that writes each committed run and each
demonstration they follow into `dist/runs/` as the tars a release attaches,
beside the manifest listing them.
"""

from cyclopts import Parameter
from typing   import Annotated

from squirtl.cli.logs         import listen, refusing
from squirtl.docs.results     import ReleaseSettings
from squirtl.releases.schemas import ReleaseManifest


def pack(
    *,
    settings: Annotated[ReleaseSettings | None, Parameter(name="*")] = None
) -> str:
    """
    Writes each run `docs/runs/` lists, and each demonstration those runs
    follow, into `dist/runs/` as the Zstandard tar a release attaches,
    beside the `manifest.json` listing each tar and its SHA-256 digest.

    Each run is read from its directory under `data/runs/`, and its tar
    holds its `run.json`, its `episodes.jsonl`, and a checkpoint holding
    the agent's weights alone, with no optimizer state and no replay memory.
    Every `run.json` packed names the cartridge `data/rom.gb`, and a run
    whose files are unchanged packs into the same bytes.

    Prints the folder holding the tars. A run whose directory holds no
    record, no checkpoint, or no episodes, or a `--recommended-run` naming
    none of the runs, exits 1.
    """
    listen()

    with refusing(OSError, ValueError):
        ReleaseManifest.pack(settings or ReleaseSettings())

    return str(ReleaseManifest.folder)
