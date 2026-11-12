<!-- help -->

# `squirtl evaluate`

Evaluates the agent of each run at its last checkpoint, over the episodes the run's settings record, beside the random baseline under the same seeds, and writes each evaluation into its run's directory, reading in place of playing any the run already holds. The deep Q-network and PQN play at the epsilon those settings record, and PPO takes its most likely action at every step.

The runs are the ones the directories hold, or the runs `--release` attaches, each fetched into `data/runs/` where it is missing there. `--agent`, `--start`, and `--seed` select among the release's runs, and without them every seed of the recommended run's agent and start plays.

Prints as Markdown each run's measures, then each measure's interquartile mean across the runs with its 95% percentile bootstrap interval and the count of runs behind it, then the probability that the agent beats its baseline, and the runs `--against` names where it names any, on each run's mean return.

Both directories and `--release`, or neither, a directory holding no run, a release GitHub does not publish or one attaching no manifest, a selection matching none of its runs, a download whose digest differs or whose tar does not unpack, or runs ending their episodes at more than one goal, whose shares reaching it do not compare, exits 1 before any evaluation. A run holding no checkpoint, holding a damaged one, reading a cartridge the emulator refuses, or recording another digest than the state its intro leaves on the cartridge exits 1, keeping the evaluations already written for the runs evaluated before it.

```console
squirtl evaluate [OPTIONS] [ARGS]
```

<!-- /help -->

<!-- settings -->

## Settings

| **Flag** | **Default** | **What It Sets** |
|---|---|---|
| `DIRECTORIES`, `--directories` | `none` | *The directory of each run whose agent to evaluate.* |
| `--against` | `none` | *The directory of each run of another agent to compare the first runs against.* |
| `--release` | `none` | *The tag of the release to read the runs from.* |
| `--agent` | `none` | *The agent the run trained.* |
| `--seed` | `none` | *The seed the run's random draws derive from.* |
| `--start` | `none` | *Where the run's training episodes start.* |

<!-- /settings -->
