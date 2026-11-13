# The Most Likely Press

Each PPO evaluation plays its episodes a second time under the same seeds taking its most likely press at every step, as [The Episodes](../methods/evaluation.md#the-episodes) sets out, while the [learning curves](./curves.md) and the [comparison against random presses](./comparison.md) read the sampled episodes alone. Each PPO seed's count of the sampled episodes reaching the goal stands here one evaluation at a time, beside its count at the most likely press wherever the two counts differ.
