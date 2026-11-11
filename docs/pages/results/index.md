# Results

Each comparison below plays a trained agent from Blue's bedroom beside random presses under the same seeds, so the two players meet the same draws of the game's randomness, and reports each figure's interquartile mean across runs with its 95% percentile bootstrap interval and the count of runs behind it, the aggregate Agarwal et al.[^agarwal2021] recommend over a handful of runs.

## The Runs

Each run the charts draw sits under `docs/runs/` as the `run.json`, `evaluations.jsonl`, and `baseline.json` it wrote, one directory per run named as the run is, and `mise write` reads them into the data every chart here draws from, so a fresh clone redraws each one. A run enters only once it has trained against the default cartridge path `data/rom.gb` and followed no demonstration at an absolute path, so no local path enters the tree. Every run here ends its episodes at one goal, `EVENT_GOT_STARTER`, as `--environment.goal` sets by default, and `mise write` refuses runs ending at more than one, since no chart sets their shares side by side. Each release attaches these runs with the weights of their last checkpoints, as [The Released Runs](../methods/evaluation.md#the-released-runs) sets out.

## Learning Curves

Each line follows the interquartile mean across one agent's runs of the share of evaluation episodes reaching the runs' goal at each evaluation, dashed where the runs trained along the curriculum, beside the share random presses reach across every run's seed. A glyph from the game marks each agent at every evaluation, the menu's cursor for PPO, the text box's prompt for PQN, and a map's block for the deep Q-network, solid from the bedroom and hollow along the curriculum.

## Against Random Presses

Each agent's runs, PQN's and PPO's trained with and without the curriculum, take a lane of their own, each run a row of cells along the steps shaded by its share of evaluation episodes reaching its goal, and at the lane's end each run's last evaluation beside the share random presses reach under its seed. A lane's verdict against random presses reads the 95% interval of the probability that a run of the agent beats a run of random presses on mean return, clearing even odds or not, and a lane trained along the curriculum adds the same probability against the agent's runs from the bedroom.

[^agarwal2021]: Agarwal et al. 2021. "Deep Reinforcement Learning at the Edge of the Statistical Precipice." *Advances in Neural Information Processing Systems* 34: 29304–29320. <https://proceedings.neurips.cc/paper/2021/hash/f514cec81cb148559cf475e7426eed5e-Abstract.html>
