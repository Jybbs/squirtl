# `squirtl pack`

Writes each run `docs/runs/` lists, and each demonstration those runs follow, into `dist/runs/` as the Zstandard tar a release attaches, beside the `manifest.json` listing each tar and its SHA-256 digest.

Each run is read from its directory under `data/runs/`, and its tar holds its `run.json`, its `episodes.jsonl`, and a checkpoint holding the agent's weights alone, with no optimizer state and no replay memory. Every `run.json` packed names the cartridge `data/rom.gb`, and a run whose files are unchanged packs into the same bytes.

Prints the folder holding the tars. A run whose directory holds no record, no checkpoint, or no episodes, or a `--recommended-run` naming none of the runs, exits 1.

```console
squirtl pack [OPTIONS]
```

## Settings

| **Flag** | **Default** | **What It Sets** |
|---|---|---|
| `--recommended-run` | `20261111T020527.724383Z` | *The name of the run a release plays where no selection names one.* |
