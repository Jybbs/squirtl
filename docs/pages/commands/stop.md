<!-- help -->

# `squirtl stop`

Writes the stop file into a training run's directory from any shell, ending the run with a checkpoint and exit status 0, as a first interrupt does, at the end of its episode for the deep Q-network and once a rollout's update ends for PQN and PPO.

A directory holding no run exits 1.

```console
squirtl stop DIRECTORY
```

<!-- /help -->

<!-- settings -->

## Settings

| **Flag** | **Default** | **What It Sets** |
|---|---|---|
| `DIRECTORY`, `--directory` | *required* | *The run's directory under `data/runs/`.* |

<!-- /settings -->
