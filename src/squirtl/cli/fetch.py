"""
Defines `fetch`, the command that unpacks the runs a release attaches into
`data/runs/`.
"""

from loguru import logger

from squirtl.cli.logs         import listen, refusing
from squirtl.cli.runs         import ReleaseTag, Selection
from squirtl.releases.schemas import GithubRelease


def fetch(*, release: ReleaseTag = None, selector: Selection = None):
    """
    Downloads the runs a release attaches and unpacks each into
    `data/runs/`, from the release `--release` names or else the latest one.

    `--agent`, `--start`, and `--seed` select among the release's trained
    runs, and without them every run and each demonstration is fetched. A
    run `data/runs/` already holds downloads nothing. Each download shows a
    progress bar and is checked against the SHA-256 digests GitHub and the
    release's manifest record for it before it is unpacked.

    Logs the directory of each run. A release GitHub does not publish,
    one attaching no manifest, a selection matching none of its runs, or a
    download whose digest differs or whose tar does not unpack exits 1.
    """
    listen()

    with refusing(OSError, ValueError):
        published = GithubRelease.read(release)

        for listing in published.matched(selector):
            logger.info("Fetched {}", published.fetch(listing).directory)
