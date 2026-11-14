<!-- help -->

# `squirtl fetch`

Downloads the runs a release attaches and unpacks each into `data/runs/`, from the release `--release` names or else the latest one.

`--agent`, `--start`, and `--seed` select among the release's trained runs, and without them every run and each demonstration is fetched. A run `data/runs/` already holds downloads nothing. Each download shows a progress bar and is checked against the SHA-256 digests GitHub and the release's manifest record for it before it is unpacked.

Logs the directory of each run. A release GitHub does not publish, one attaching no manifest, a selection matching none of its runs, or a download whose digest differs or whose tar does not unpack exits 1.

```console
squirtl fetch [OPTIONS]
```

<!-- /help -->

A fetch unpacks each tar into `data/runs/` only once the digest of its download matches both the one GitHub carries for the asset and the one the release's manifest records. The widget below runs `squirtl fetch --agent dqn` against a made-up release attaching the deep Q-network's runs that the [Results](../results/index.md) section draws, with every tar's size and digest made up. In the release whose tar of one run was altered after packing, the fetch stops at that run, whose download matches GitHub's digest and differs from the manifest's.

<!-- settings -->

## Settings

| **Flag** | **Default** | **What It Sets** |
|---|---|---|
| `--release` | `none` | *The tag of the release to read the runs from.* |
| `--agent` | `none` | *The agent the run trained.* |
| `--seed` | `none` | *The seed the run's random draws derive from.* |
| `--start` | `none` | *Where the run's training episodes start.* |

<!-- /settings -->
