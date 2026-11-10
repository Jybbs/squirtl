# `squirtl fetch`

Downloads the runs a release attaches and unpacks each into `data/runs/`, from the release `--release` names or else the latest one.

`--agent`, `--start`, and `--seed` select among the release's runs, and without them every run and each demonstration they follow is fetched. A run `data/runs/` already holds downloads nothing. Each download shows a progress bar and is checked against the SHA-256 digests GitHub and the release's manifest record for it before it is unpacked.

Logs the directory of each run. A release GitHub does not publish, one attaching no manifest, a selection matching none of its runs, or a download whose digest differs or whose tar does not unpack exits 1.

```console
squirtl fetch [OPTIONS]
```

## Settings

| **Flag** | **Default** | **What It Sets** |
|---|---|---|
| `--release` | `none` | *The tag of the release to read the runs from.* |
| `--agent` | `none` | *The agent the run trained.* |
| `--seed` | `none` | *The seed the run's random draws derive from.* |
| `--start` | `none` | *Where the run's training episodes start.* |
