# Against Random Presses

Each agent's runs, PQN's and PPO's trained with and without the curriculum, take a lane of their own, each run a row of cells along the steps shaded by its share of evaluation episodes reaching its goal, and at the lane's end each run's last evaluation beside the share random presses reach under its seed. A lane's verdict against random presses reads the 95% interval of the probability that a run of the agent beats a run of random presses on mean return, the probability of improvement Agarwal et al.[^agarwal2021] define, clearing even odds or not, and a lane trained along the curriculum adds the same probability against the agent's runs from the bedroom.

[^agarwal2021]: Agarwal et al. 2021. "Deep Reinforcement Learning at the Edge of the Statistical Precipice." *Advances in Neural Information Processing Systems* 34: 29304–29320. <https://proceedings.neurips.cc/paper/2021/hash/f514cec81cb148559cf475e7426eed5e-Abstract.html>
