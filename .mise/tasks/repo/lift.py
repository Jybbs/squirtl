#!/usr/bin/env -S uv run --exact --locked
# MISE alias       = "lift"
# MISE description = "Report each pin lagging its newest release, and try or write it"
# USAGE flag "--hold <pin>" var=#true help="Leave a pin where it stands for this run"
# USAGE flag "--try" help="Lift every pin in a scratch clone and run mise ci there"
# USAGE flag "--write" help="Write every lift into the checkout, once any trial passes"
"""
Prints one table of every pin lagging its newest release, through `Lifts`
in `squirtl.repo.lifts`, as the `repo:lift` task. Under `--try`, it lifts
every pin in a scratch clone and runs `mise ci` there, and under `--write`,
it writes every lift into the checkout, after a passing trial where both
are given. Each leaves the pins `.mise/holds.toml` and `--hold` name where
they stand, beside each pin paired with one, and leaves `min_version` where
it stands while the running mise is older than its newest release. The task
exits 2 where a hold names a pin the table does not list, and 1 where the
trial fails.
"""

from os import environ

from squirtl.repo.lifts import Lifts

if __name__ == "__main__":

    raise SystemExit(
        Lifts.read().lift(
            held    = environ.get("usage_hold", "").split(),
            trying  = environ.get("usage_try") == "true",
            writing = environ.get("usage_write") == "true"
        )
    )
