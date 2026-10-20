#!/usr/bin/env -S uv run --exact --locked
# MISE alias       = "audit"
# MISE description = "Fail on each pin, registry, or layout rule a file departs from"
"""
Runs every check `squirtl.repo.checks` declares over the checkout, as the
`repo:audit` task the `🗺️ Audit` row of `🕹️ CI` runs. The task prints each
finding as the workflow command GitHub shows as an annotation on its file
and line, a file that fails to parse among them, and exits 1 where any
finding is an error rather than a warning.
"""

from squirtl.repo.checks import Audit

if __name__ == "__main__":

    raise SystemExit(Audit.read().report())
