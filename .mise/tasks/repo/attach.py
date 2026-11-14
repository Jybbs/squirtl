#!/usr/bin/env -S uv run --exact --locked
# MISE alias       = "attach"
# MISE description = "Attach the packed runs to the draft release, once confirmed"
"""
Attaches the trained runs to the draft release of the version the package
carries, as the `repo:attach` task. The task packs every committed run
as `squirtl pack` does, prints the `gh release upload --clobber` command
sending each tar and the manifest, and sends it once the reader confirms it,
so attaching again replaces each asset.
"""

from importlib.metadata import version

from squirtl.releases.schemas import ReleaseManifest
from squirtl.repo.github      import Command, Plan

if __name__ == "__main__":

    manifest = ReleaseManifest.pack()
    raise SystemExit(
        Plan(
            writes = (
                Command(
                    arguments = (
                        "release", "upload",
                        version("squirtl"),
                        *map(str, manifest.files),
                        "--clobber"
                    )
                ),
            )
        ).apply()
    )
