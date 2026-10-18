#!/usr/bin/env -S uv run --exact --locked
# MISE alias       = "labels"
# MISE description = "Write the labels `.github/labels.toml` declares, once confirmed"
"""
Brings the repository's labels in line with `.github/labels.toml`, as the
`repo:labels` task. The task prints each label GitHub lacks or carries under
another color or description as the `gh label create --force` command that
writes it, sends those commands once the reader confirms them, and lists
each label GitHub carries that the registry leaves out rather than deleting
it.
"""

from squirtl.repo.schemas import Labels

if __name__ == "__main__":

    raise SystemExit(Labels.read().plan.apply())
