<!-- help -->

# `squirtl pack`

Writes each run `docs/runs/` lists, and each demonstration those runs follow, into `dist/runs/` as the Zstandard tar a release attaches, beside the `manifest.json` listing each tar and its SHA-256 digest.

Each run is read from its directory under `data/runs/`, and its tar holds its `run.json`, its `episodes.jsonl`, and a checkpoint holding the agent's weights alone, with no optimizer state and no replay memory. Every `run.json` packed names the cartridge `data/rom.gb`, and a run whose files are unchanged packs into the same bytes.

Prints the folder holding the tars. Each of these exits 1 before any tar is written:

- A `--recommended-run` naming none of the trained runs
- A run whose directory holds no record, no checkpoint, or no episodes
- A run holding a line of episodes `squirtl watch` cannot read

```console
squirtl pack [OPTIONS]
```

<!-- /help -->

A pack writes the tar of each demonstration and then the tar of each trained run, recording every tar's SHA-256 digest in the `manifest.json` that `squirtl fetch` checks each download against. The widget below packs the runs the [Results](../results/index.md) section draws and the demonstration they follow, filling each tar's entry in `manifest.json` with a made-up digest once the tar is written.

<!-- settings -->

## Settings

| **Flag** | **Default** | **What It Sets** |
|---|---|---|
| `--recommended-run` | `20261112T141501.166143Z` | *The name of the run a release plays where no selection names one.* |

<!-- /settings -->
