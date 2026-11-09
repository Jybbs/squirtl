# Results

Each comparison below plays a trained agent from Blue's bedroom beside random presses under the same seeds, so the two players meet the same draws of the game's randomness, and reports each figure's interquartile mean across runs with its 95% percentile bootstrap interval and the count of runs behind it, the aggregate Agarwal et al.[^agarwal2021] recommend over a handful of runs.

## The Runs

Each run the charts draw sits under `docs/runs/` as the `run.json`, `evaluations.jsonl`, and `baseline.json` it wrote, one directory per run named as the run is, and `mise write` reads them into the data every chart here draws from, so a fresh clone redraws each one. A run enters only once it has trained against the default cartridge path `data/rom.gb`, so no local path enters the tree.

## Learning Curves

Each line follows one run's share of evaluation episodes reaching the starter at each evaluation it played, beside the share random presses reach under the same seeds.

## Against Random Presses

Each agent's runs, PQN's and PPO's trained with and without the curriculum, sit beside the random baseline's at each run's last evaluation, with the probability that a run of the agent beats a run of random presses on mean return.

[^agarwal2021]: Agarwal et al. 2021. "Deep Reinforcement Learning at the Edge of the Statistical Precipice." *Advances in Neural Information Processing Systems* 34: 29304–29320. <https://proceedings.neurips.cc/paper/2021/hash/f514cec81cb148559cf475e7426eed5e-Abstract.html>
