#!/usr/bin/env python3
# MISE description = "Fail on an advisory against a tool `.mise/config.toml` pins"
"""
Looks up each tool `[tools]` in `.mise/config.toml` pins through `mise
audit`, as the last step of `lock:check`, so a tool a reader's global mise
config adds stays out of the result. `Audit` reads each advisory the audit
reports as an `Advisory` and passes one `AUDIT_IGNORE` lists, by its id or
an alias, only while it names no fixed version and the newest release of the
pin's line, its first two parts, still carries it, since `mise audit` lists
no fixed version for a fix recorded as a commit. The task prints a line per
failing advisory to standard error and exits 1 where any advisory fails or
where `mise` itself fails, as it does without the network or on a pin that
resolves to no version.
"""

from dataclasses import dataclass, fields
from json        import loads
from os          import environ
from pathlib     import Path
from subprocess  import run
from sys         import stderr
from tomllib     import loads as read_toml
from typing      import Self


def mise(*args: str) -> str:
    """
    Runs `mise` with `args`, under `MISE_QUIET` and `MISE_VERBOSE` so a
    reader's debug logging leaves only errors on standard error, which tells
    an error apart from the exit 1 `mise audit` takes on an advisory.

    Returns:
        What `mise` printed to standard output, the task stopping on what it
        printed to standard error, or where it printed nothing.
    """
    result = run(
        ["mise", *args],
        capture_output = True,
        env            = {**environ, "MISE_QUIET": "1", "MISE_VERBOSE": "0"},
        text           = True
    )

    if result.stderr or not result.stdout:
        raise SystemExit(result.stderr.strip() or f"mise {args[0]} printed nothing")

    return result.stdout


@dataclass(frozen=True, kw_only=True)
class Advisory:
    """
    One advisory against a tool version, holding the fields `mise audit
    --json` lists it under, `aliases` being the other ids it is published
    under and `fixed` every version that fixes it.
    """

    aliases : list[str]
    fixed   : list[str]
    id      : str
    summary : str
    tool    : str
    version : str

    def failure(self, ignored: set[str]) -> str | None:
        """
        Describes why the advisory fails the task.

        Returns:
            A line naming the advisory, the tool, and its version, beside the
            versions to lift to once a release fixes it, or `None` where
            `ignored` lists the advisory or one of its aliases, it names no
            fixed version, and the newest release of the pin's line still
            carries it.
        """
        fixes  = ", ".join(self.fixed)
        listed = " ".join(sorted(ignored.intersection([self.id, *self.aliases])))

        if not listed:
            lift = f", fixed in {fixes}" if fixes else ""
            return f"{self.id} affects {self.tool} {self.version}{lift}: {self.summary}"

        if fixes:
            return (
                f"{self.id} is fixed in {fixes}, so delete {listed} from "
                f"AUDIT_IGNORE in .mise/config.toml and lift {self.tool} "
                f"{self.version} to a fixed version"
            )

        line   = ".".join(self.version.split(".")[:2])
        newest = mise("latest", f"{self.tool}@{line}").strip()

        if (
            newest     == self.version
            or self.id in Audit.from_mise(f"{self.tool}@{newest}")
        ):
            return None

        return (
            f"{self.id} no longer affects {self.tool} {newest}, so delete "
            f"{listed} from AUDIT_IGNORE in .mise/config.toml and lift "
            f"{self.tool} {self.version} to {newest}"
        )


@dataclass(frozen=True)
class Audit:
    """
    The advisories `mise audit` reports against the tools it checks.
    """

    advisories: list[Advisory]

    def __contains__(self, key: str) -> bool:
        """
        Tells whether the audit reports the advisory whose id is `key`.
        """
        return any(advisory.id == key for advisory in self.advisories)

    @classmethod
    def from_mise(cls, *tools: str) -> Self:
        """
        Runs `mise audit` over each of `tools`, or each tool `[tools]` in
        `.mise/config.toml` names where `tools` is empty.
        """
        config = Path(environ["MISE_PROJECT_ROOT"], ".mise/config.toml")
        tools  = tools or tuple(read_toml(config.read_text(encoding="utf-8"))["tools"])

        return cls(
            [
                Advisory(
                    **{field.name: finding[field.name] for field in fields(Advisory)}
                )
                for finding in loads(mise("audit", "--json", *tools))["vulnerabilities"]
            ]
        )

    def report(self) -> int:
        """
        Prints a line to standard error per advisory that fails the
        task, reading the advisories `AUDIT_IGNORE` lists, separated by
        whitespace.

        Returns:
            The task's exit status, 1 where any advisory fails.
        """
        ignored  = set(environ.get("AUDIT_IGNORE", "").split())
        failures = [
            line
            for advisory in self.advisories
            if (line := advisory.failure(ignored))
        ]

        for line in failures:
            print(line, file=stderr)

        return int(bool(failures))


if __name__ == "__main__":

    raise SystemExit(Audit.from_mise().report())
