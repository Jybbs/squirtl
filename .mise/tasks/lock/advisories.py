#!/usr/bin/env python3
# MISE description = "Fail on an advisory against a tool `.mise/config.toml` pins"
"""
Looks up each tool `[tools]` in `.mise/config.toml` pins through `mise
audit`, as the last step of `lock:check`, so a tool a reader's global mise
config adds stays out of the result. `Audit` reads each advisory the audit
reports as an `Advisory` and passes one `AUDIT_IGNORE` lists, by its id or
an alias, only while it names no fixed version. The task prints a line per
failing advisory to standard error and exits 1 where any advisory fails or
where `mise audit` itself fails, as it does without the network or on a pin
that resolves to no version.
"""

from dataclasses import dataclass, fields
from json        import loads
from os          import environ
from pathlib     import Path
from subprocess  import run
from sys         import stderr
from tomllib     import loads as read_toml
from typing      import Self


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
            `ignored` lists the advisory or one of its aliases and no release
            fixes it yet.
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

        return None


@dataclass(frozen=True)
class Audit:
    """
    The advisories `mise audit` reports against the tools the project pins.
    """

    advisories: list[Advisory]

    @classmethod
    def from_mise(cls) -> Self:
        """
        Runs `mise audit` over each tool `[tools]` in `.mise/config.toml`
        names, and stops the task where it fails for any reason but an
        advisory, which `--quiet` tells apart by leaving only errors on
        standard error, as `MISE_QUIET` and `MISE_VERBOSE` hold it to under
        a reader's debug logging.
        """
        config = Path(environ["MISE_PROJECT_ROOT"], ".mise/config.toml")
        tools  = read_toml(config.read_text(encoding="utf-8"))["tools"]
        audit  = run(
            ["mise", "audit", "--json", "--quiet", *tools],
            capture_output = True,
            env            = {**environ, "MISE_QUIET": "1", "MISE_VERBOSE": "0"},
            text           = True
        )

        if audit.stderr or not audit.stdout:
            raise SystemExit(audit.stderr.strip() or "mise audit printed no report")

        return cls(
            [
                Advisory(
                    **{field.name: finding[field.name] for field in fields(Advisory)}
                )
                for finding in loads(audit.stdout)["vulnerabilities"]
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
