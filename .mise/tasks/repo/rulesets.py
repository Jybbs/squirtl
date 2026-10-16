#!/usr/bin/env -S uv run --exact --locked
# MISE alias       = "rulesets"
# MISE description = "Apply the rulesets and the repository settings, once confirmed"
"""
Applies the rulesets under `.github/rulesets/` and then the repository
settings `.github/settings.toml` declares, as the `repo:rulesets` task.
The task prints every `gh api` command it sends, the rulesets first, each
updating in place the ruleset GitHub carries under its name or creating one
where GitHub carries none, and every setting after them. It sends them once
the reader confirms them, and lists each ruleset GitHub carries that no file
declares rather than deleting it.
"""

from squirtl.repo.schemas import Rulesets, Settings

if __name__ == "__main__":

    raise SystemExit((Rulesets.read().plan + Settings.read().plan).apply())
