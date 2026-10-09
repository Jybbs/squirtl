#!/usr/bin/env python3
# MISE description = "Delete the Actions cache entries that newer entries replaced"
"""
Deletes the Actions cache entries that newer entries have replaced, as
the `gha:prune` task the `🧹 Prune` job of `🕹️ Warm` runs on the runner's
own interpreter and the `gh` it carries. `Caches` reads every entry as an
`Entry`, keeps the newest entry of each generation, and deletes the rest
through `gh cache delete`, which needs the `actions: write` permission the
job declares. It prints a line per deleted entry and then the bytes freed.
"""

from dataclasses import dataclass, fields
from datetime    import datetime
from json        import loads
from operator    import attrgetter
from subprocess  import CompletedProcess, run
from typing      import Self


def gh(*arguments: str) -> CompletedProcess[str]:
    """
    Runs `gh` with `arguments`, capturing both output streams as text.
    """
    return run(["gh", *arguments], capture_output=True, text=True)


@dataclass(frozen=True, kw_only=True)
class Entry:
    """
    One Actions cache entry, holding the fields `gh cache list --json`
    returns for it under the names `gh` gives them.
    """

    createdAt   : str
    id          : int
    key         : str
    ref         : str
    sizeInBytes : int

    @property
    def created(self) -> datetime:
        """
        Reads the instant GitHub created the entry at, which `createdAt`
        holds as an ISO 8601 timestamp.
        """
        return datetime.fromisoformat(self.createdAt)

    @property
    def generation(self) -> tuple[str, str] | None:
        """
        Names the generation the entry belongs to, which every version of
        one cache shares, since a workflow run saving a cache writes a key
        ending in a hash of the files its contents come from.

        Returns:
            The branch or pull request that saved the entry beside its key
            up to the last `-`, or `None` for a key holding no `-`, which
            belongs to no generation.
        """
        prefix, dash, _ = self.key.rpartition("-")
        return (self.ref, prefix) if dash else None

    def delete(self) -> bool:
        """
        Deletes the entry through `gh cache delete`, printing its key and
        size where GitHub accepts the request and a warning carrying the
        error `gh` reported where GitHub refuses it.

        Returns:
            Whether GitHub accepted the request.
        """
        deletion = gh("cache", "delete", str(self.id))

        if deletion.returncode:
            print(f"::warning::{self.key} not deleted, {deletion.stderr.strip()}")
            return False

        print(f"{self.key} deleted, {self.sizeInBytes} bytes")
        return True


@dataclass(frozen=True)
class Caches:
    """
    The cache entries the repository holds, as `gh cache list` lists them.
    """

    entries: list[Entry]

    @property
    def replaced(self) -> list[Entry]:
        """
        Sets aside every entry a newer entry of its generation replaces,
        leaving each generation's newest entry and every entry belonging to
        no generation.

        Returns:
            The replaced entries, in the order the listing holds them.
        """
        newest = {
            entry.generation: entry
            for entry in sorted(self.entries, key=attrgetter("created"))
        }

        return [
            entry
            for entry in self.entries
            if entry.generation and newest[entry.generation] is not entry
        ]

    @classmethod
    def from_github(cls) -> Self:
        """
        Reads every entry `gh cache list` returns, asking for each field
        `Entry` declares, and stops the task where the listing fails.
        """
        # Without `--limit`, `gh cache list` returns at most 30 entries.
        listing = gh(
            "cache",
            "list",
            "--json",
            ",".join(field.name for field in fields(Entry)),
            "--limit",
            "100"
        )

        if listing.returncode:
            raise SystemExit(f"::error::gh cache list failed, {listing.stderr.strip()}")

        return cls([Entry(**row) for row in loads(listing.stdout)])

    def prune(self):
        """
        Deletes every replaced entry, then prints how many of them GitHub
        deleted and how many bytes that freed.
        """
        stale   = self.replaced
        removed = [entry for entry in stale if entry.delete()]

        print(
            f"{len(removed)} of {len(stale)} replaced entries deleted, "
            f"{sum(entry.sizeInBytes for entry in removed)} bytes freed"
        )


if __name__ == "__main__":

    Caches.from_github().prune()
