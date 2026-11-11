<!-- help -->

# `squirtl watch`

Opens the emulator's window and plays back one episode the run recorded, from the reset at the `timer_div` the run recorded for it to the return the run recorded, at the sixty steps a second the window paces.

The run is the one a directory holds, or one of the runs `--release` attaches, fetched into `data/runs/` where it is missing there. `--agent`, `--start`, and `--seed` select it among the release's runs, and without them the release's recommended run plays.

An episode that started along a demonstration plays the demonstration's presses up to its start first, and its return counts its own steps alone.

Each of these exits 1 before the window opens:

- Both a directory and `--release`, or neither
- A directory holding no run, a release GitHub does not publish, or one attaching no manifest
- A download whose digest differs or whose tar does not unpack
- A selection matching no run of the release, or more than one, each of which it names
- An episode the run never recorded, or a cartridge the emulator refuses

A console whose intro leaves a state of another digest than the run's exits 1 before playing anything, and a playback reaching a return other than the one recorded exits 1 once it ends.

```console
squirtl watch [OPTIONS] [ARGS]
```

<!-- /help -->

A playback presses the buttons the run recorded for its episode, checking the state the intro leaves against the run's digest before the first press and the return it reaches against the recorded one after the last. The widget below plays back an episode that a stand-in for the agent pressed through a model of the first rooms, with a made-up digest and `timer_div` standing in for the ones a run's `run.json` and `episodes.jsonl` record.

<!-- settings -->

## Settings

| **Flag** | **Default** | **What It Sets** |
|---|---|---|
| `DIRECTORY`, `--directory` | `none` | *The run's directory under `data/runs/`.* |
| `--episode` | `none` | *The episode to play, counting from 1, or none for the last.* |
| `--release` | `none` | *The tag of the release to read the runs from.* |
| `--agent` | `none` | *The agent the run trained.* |
| `--seed` | `none` | *The seed the run's random draws derive from.* |
| `--start` | `none` | *Where the run's training episodes start.* |

<!-- /settings -->
