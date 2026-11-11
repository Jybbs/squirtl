# Evaluation

An evaluation plays a trained agent's episodes from Blue's bedroom beside the same count of episodes of random presses under the same seeds, so a comparison sets the agent against what pressing at random reaches with the same draws of the game's randomness. A run plays one every 250,000 steps, and `squirtl evaluate` plays one at a run's last checkpoint.

## The Episodes

Each evaluation plays 30 episodes of each player, the count Mnih et al.[^mnih2015] evaluate over. The deep Q-network and PQN choose a random press with probability 0.05 at each step, the epsilon Mnih et al. evaluate at, whereas PPO takes its most likely press at every step. Random presses choose uniformly among the seven presses at every step.

## The Measures

Each evaluation averages over each player's episodes the share reaching the starter, the steps the episodes reaching it took, the positions reached, the return, and each term's part of that return. Across runs, each measure is reported as its interquartile mean, the mean of the runs left once a quarter is cut from each end, with its 95% percentile bootstrap interval and the count of runs behind it, as Agarwal et al.[^agarwal2021] aggregate a handful of runs. The comparison of one agent against random presses, or against another agent, is the probability that a run of the first beats a run of the second on mean return, which the Mann-Whitney statistic over every pair of runs estimates.

## The Released Runs

Each release attaches every run the [Results](../results/index.md) page measures, each holding its settings, its recorded episodes, and the weights of its last checkpoint, with no optimizer state and no replay memory. `squirtl fetch` unpacks a release's runs under `data/runs/`, and `squirtl evaluate --release <tag>` measures again the runs `--agent`, `--start`, and `--seed` select, or every seed of the recommended run's agent and start without them, on a cartridge at `data/rom.gb`, refusing one whose intro leaves the console in another state than the run recorded. A fetched run holds no evaluation, so every episode plays afresh.

## Settings

The table below is written from the help `squirtl train` prints for each `--evaluation.` setting, and `mise write` rewrites it.

<!-- settings:evaluation -->

| **Flag** | **Default** | **What It Sets** |
|---|---|---|
| `--evaluation.environments` | *the machine's* | *The environments an evaluation plays its episodes across in parallel, each in a worker process of its own, which defaults to the CPUs the process may use.* |
| `--evaluation.episodes` | `30` | *The episodes each evaluation plays of the agent and of the random baseline, whose default follows Mnih et al.* |
| `--evaluation.epsilon` | `0.05` | *The chance of a random action at each step of an evaluation episode of the deep Q-network or of PQN, whose default follows Mnih et al. PPO takes its most likely action at every step.* |

<!-- /settings:evaluation -->

[^mnih2015]: Mnih et al. 2015. "Human-level control through deep reinforcement learning." *Nature* 518(7540): 529–533. <https://doi.org/10.1038/nature14236>

[^agarwal2021]: Agarwal et al. 2021. "Deep Reinforcement Learning at the Edge of the Statistical Precipice." *Advances in Neural Information Processing Systems* 34: 29304–29320. <https://proceedings.neurips.cc/paper/2021/hash/f514cec81cb148559cf475e7426eed5e-Abstract.html>
