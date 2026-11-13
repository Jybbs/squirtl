# Results

Each comparison in this section plays a trained agent from Blue's bedroom beside random presses under the same seeds, so the two players meet the same draws of the game's randomness, and reports each figure's interquartile mean across runs with its 95% percentile bootstrap interval and the count of runs behind it, the aggregate Agarwal et al.[^agarwal2021] recommend over a handful of runs.

## The Comparisons

Each comparison sits on a page of its own, closing on the chart it draws:

- [Learning Curves](./curves.md) follows each agent's share of evaluation episodes reaching the goal across training, beside the share random presses reach
- [Against Random Presses](./comparison.md) sets each run's last evaluation beside random presses under its seed, with each agent's verdict against them
- [The Most Likely Press](./most-likely.md) sets each PPO seed's sampled episodes beside its episodes at the most likely press

## The Runs

Each run the section's charts draw sits under `docs/runs/` as the `run.json`, `evaluations.jsonl`, and `baseline.json` it wrote, one directory per run named as the run is, and `mise write` reads them into the data every chart in this section draws from, so a fresh clone redraws each one. A run enters only once it has trained against the default cartridge path `data/rom.gb` and followed no demonstration at an absolute path, so no local path enters the tree. Every run here ends its episodes at one goal, `EVENT_GOT_STARTER`, as `--environment.goal` sets by default, and `mise write` refuses runs ending at more than one, since no chart sets their shares side by side. Each release attaches these runs with the weights of their last checkpoints, as [The Released Runs](../methods/evaluation.md#the-released-runs) sets out.

[^agarwal2021]: Agarwal et al. 2021. "Deep Reinforcement Learning at the Edge of the Statistical Precipice." *Advances in Neural Information Processing Systems* 34: 29304–29320. <https://proceedings.neurips.cc/paper/2021/hash/f514cec81cb148559cf475e7426eed5e-Abstract.html>
