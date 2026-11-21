#!/usr/bin/env -S uv run --exact --locked --script
# MISE description = "Combine the coverage parts and report against `fail_under`"
# MISE wait_for    = ["py:split"]
# /// script
# dependencies    = ["coverage==7.17.3"]
# requires-python = ">=3.15"
# ///
"""
Combines the coverage data of a split run of the suite as the `py:combine`
task, which the combining job of `🕹️ CI` runs once each machine's data file
sits at `.cache/coverage/parts/<machine>/data`. It then writes the HTML
report, the JSON report, and the terminal table from the combined data,
where the `[tool.coverage]` tables in `pyproject.toml` set each report's
path and the gate. Where no part exists, as after `py:split` on a laptop, it
reports on the data that run wrote.
"""

from coverage.cmdline import main
from pathlib          import Path


def combine(parts: Path) -> int:
    """
    Combines each data file under `parts` into the configured data file,
    then writes every report from it, each report checking the total against
    `fail_under` on its own.

    Returns:
        The status of the combine where it failed, and otherwise the
        highest status a report returned, which is `2` where the total
        falls below `fail_under`.
    """
    if (files := sorted(map(str, parts.glob("*/data")))) and (
        failed := main(["combine", *files])
    ):
        return failed

    return max(main([report]) for report in ("html", "json", "report"))


if __name__ == "__main__":

    raise SystemExit(combine(Path(".cache/coverage/parts")))
