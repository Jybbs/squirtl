# Agents

Each agent learns which press to make from what the screen shows, valuing a press by the reward it earns and by what the state it reaches is worth to the steps after it. A run trains one of three agents, the deep Q-network, PQN, or PPO, each reading an observation through the same layers, Mnih et al.'s[^mnih2015] convolutions over the stacked frames beside an encoder for the grid and one for the flags, joined by fully connected layers of 512 units as Pleines et al.[^pleines2025] join them.

## The Discount

Every agent discounts the value of the state each step reaches by $`\gamma = 0.997`$, the discount Pleines et al. settle on for this game after tuning over 0.99, 0.997, 0.999, and 0.9995. A payment $`k`$ steps ahead counts $`\gamma^k`$ of its worth today, so at 0.997 a payment counts half once it is about 231 steps away, a walk of a few rooms.

## The Deep Q-Network

The deep Q-network values each press in each state, choosing the press its online network values highest except with probability $`\epsilon`$, when it presses at random. That probability falls linearly from 1 to 0.01 over the run's first tenth of steps and holds there:

```math
\epsilon_t = \epsilon_0 + \min\left(\frac{t}{T}, 1\right)(\epsilon_{\min} - \epsilon_0)
```

Every step it takes goes into replay memory, and once it holds 50,000 steps, the network trains on every fourth step on a batch of 32 transitions drawn uniformly from it, the replay start size and the update frequency Mnih et al. set. Each update minimizes the Huber loss $`\ell`$ on the gap between each target and the value the online network gives:

```math
L(\theta) = \mathbb{E}_{(s, a, r, s') \sim U(D)} \left[ \ell\left(y - Q(s, a; \theta)\right) \right]
```

The target follows van Hasselt et al.'s[^vanhasselt2016] Double DQN, the online network choosing the next press and the target network valuing it:

```math
y = r + \gamma \, Q\left(s', \arg\max_{a'} Q(s', a'; \theta); \theta^-\right)
```

A step that ends the episode at the starter takes $`y = r`$, whereas a step the time limit cuts short keeps the discounted term. The target network's weights $`\theta^-`$ are a copy of the online network's taken every 1,000 steps, and `--agent.double-q=false` has the target network both choose and value the next press, as Mnih et al.'s deep Q-network does.

## PQN

PQN, Gallici et al.'s[^gallici2025] parallel Q-network, values each press as the deep Q-network does but keeps neither replay memory nor a target network. It acts across 8 environments run in parallel, choosing each press epsilon-greedily, and once each environment has taken 512 steps, it trains for 2 passes over the rollout on half the squared error between its values and the λ-returns computed backward through it, with layer normalization after every layer as Gallici et al.'s Atari network normalizes.

Each environment's chance of a random press falls linearly from 1 over the run's first tenth of steps, as Gallici et al.'s Atari settings anneal it, to a floor of its own. The floors fall geometrically from 0.4 in the first of $`N`$ environments to Gallici et al.'s 0.001 in the last, as Horgan et al.[^horgan2018] spread the chances of Ape-X's actors:

```math
\epsilon_i = 0.4^{1 - i/(N - 1)} \cdot 0.001^{i/(N - 1)}
```

Gallici et al. note that the randomness of an environment's own dynamics spreads even a greedy policy across several states at once, whereas the emulator plays each press out the same way from the same state, so environments sharing one floor of 0.001 would follow a single walk. Across the default 8 environments, the floors run 0.4, 0.17, 0.072, 0.031, 0.013, 0.0055, 0.0024, and 0.001.

## PPO

PPO, Schulman et al.'s[^schulman2017] proximal policy optimization, learns a policy and a value beside it, sampling each press from the policy across the same environments run in parallel. Once each environment has taken 2,048 steps, it trains for 3 passes over the rollout toward the clipped objective, the ratio of the new policy's probability of a press to the old one's clipped within 0.2 of 1, with each advantage a generalized advantage estimate of Schulman et al.[^schulman2015] and the value's loss clipped as Pleines et al. clip it on Pokémon Red.

## Replay Memory and Rollouts

The agents differ first in where their experience comes from. The deep Q-network plays one environment and keeps each step in replay memory, which holds the last 100,000 and gives each update a batch of 32 drawn from all of them, so with an update every 4 steps, each step is drawn about 8 times on average before a newer one takes its slot. PQN and PPO play 8 environments at once, collect a rollout of every environment's steps, train on it, and then set it aside, so each step trains the network only in the passes over its own rollout, 2 for PQN and 3 for PPO.

## The Reach of an Update

The agents differ next in how far back along a walk one update carries the worth of what the walk reached. The deep Q-network's target reads the target network, so the worth of reaching a milestone moves one press further back each time the target network takes its copy. PQN's λ-returns run backward through each rollout, so one update carries the worth of a milestone back many presses at once, each press further back multiplying its weight by $`\gamma\lambda`$, so the weight falls under 1% within 11 presses at the default λ of 0.65. PPO's advantages run backward the same way, while the clip holds how far each update moves the odds of a press, so the worth spreads along the whole walk in small steps.

## Settings

The table below is written from the help `squirtl train` prints for each `--agent.` setting, and `mise write` rewrites it.

<!-- settings:agent -->

| **Flag** | **Default** | **What It Sets** |
|---|---|---|
| `--agent.algorithm` | `dqn` | *The agent the run trains, the deep Q-network, PQN, or PPO.* |
| `--agent.batch-size` | `32` | *The transitions each update of the deep Q-network draws from replay memory, whose default follows Mnih et al.* |
| `--agent.capacity` | `100000` | *The slots the deep Q-network's replay memory holds before overwriting the oldest, four per reset observation and one per step, whose default takes 606 MB for a 72 by 80 frame, a 48 by 48 grid, and four flags, the grid and the flags packed eight cells to a byte.* |
| `--agent.device` | *the machine's* | *The device every network and batch sit on, which defaults to the accelerator torch reports and to the CPU where it reports none.* |
| `--agent.discount` | `0.997` | *The discount on the value of the state each step reaches, whose default is the one Pleines et al. settle on for this game after tuning over 0.99, 0.997, 0.999, and 0.9995.* |
| `--agent.double-q` | `true` | *Whether the deep Q-network's online network chooses the action at the state each step reaches and the target network values it, as van Hasselt et al.'s Double DQN does, where otherwise the target network does both, as Mnih et al.'s deep Q-network does.* |
| `--agent.environments` | `8` | *The environments PQN and PPO collect each rollout across in parallel, each in a worker process of its own, whose default suits the ten-core machine the runs train on, where both agents step more slowly across 4 and PQN across 6, while neither steps measurably faster across 10 or 12.* |
| `--agent.epsilon-end` | `0.01` | *The deep Q-network's chance of a random action once exploration has annealed, whose default follows CleanRL's `dqn_atari.py`.* |
| `--agent.epsilon-start` | `1.0` | *The deep Q-network's chance of a random action at the run's first step, whose default follows CleanRL's `dqn_atari.py`.* |
| `--agent.exploration-fraction` | `0.1` | *The share of the run's steps over which the deep Q-network's chance of a random action falls linearly from `epsilon_start` to `epsilon_end`, whose default follows CleanRL's `dqn_atari.py`.* |
| `--agent.learning-rate` | `0.0001` | *The step size Adam takes on every update of the deep Q-network, held constant across the run, whose default follows CleanRL's `dqn_atari.py`.* |
| `--agent.max-concurrency` | `none` | *The most of PQN's and PPO's environments that step at once, which `AsyncVectorEnv` caps through a semaphore its workers share, or `None` for no cap, whose default leaves them uncapped, since a cap of 4, 6, or 8 gives PPO no consistent gain in steps per second on the ten-core machine the runs train on.* |
| `--agent.max-grad-norm` | `10.0` | *The norm each update of the deep Q-network clips its gradient to, whose default follows Stable-Baselines3's DQN.* |
| `--agent.ppo.clip-range` | `0.2` | *The distance from 1 at which each update clips the ratio of the new policy's probability of an action to the old one's, and from the old value at which it clips the new value, whose default is the clip range Pleines et al. train with on Pokémon Red.* |
| `--agent.ppo.epochs` | `3` | *The passes each update takes over the rollout, whose default is the epochs Pleines et al. train with.* |
| `--agent.ppo.learning-rate` | `0.0003` | *The step size AdamW takes on every minibatch, held constant across the run, whose default is the learning rate Pleines et al. train with.* |
| `--agent.ppo.max-grad-norm` | `0.5` | *The norm each minibatch's gradient is clipped to, whose default is the maximum gradient norm Pleines et al. train with.* |
| `--agent.ppo.minibatches` | `8` | *The minibatches each epoch splits the rollout into, whose default is the count Pleines et al. train with.* |
| `--agent.ppo.rollout-steps` | `2048` | *The steps each environment takes in a rollout, which each update then reads whole, whose default is the horizon Section III-B of Pleines et al. reports as more effective than horizons of 512 or 1024 steps.* |
| `--agent.ppo.trace-decay` | `0.95` | *The λ that weights each generalized advantage estimate of Schulman et al., whose default is the one Pleines et al. train with.* |
| `--agent.ppo.value-coefficient` | `0.5` | *The weight of the value's loss beside the clipped objective, whose default is the coefficient Pleines et al. train with.* |
| `--agent.pqn.epochs` | `2` | *The passes each update takes over the rollout, whose default is the epochs of Gallici et al.'s Atari settings.* |
| `--agent.pqn.epsilon-end` | `0.001` | *The chance of a random action the last environment anneals to, the lowest of the environments' floors, whose default is the one Gallici et al.'s Atari settings finish at.* |
| `--agent.pqn.epsilon-end-first` | `0.4` | *The chance of a random action the first environment anneals to, the highest of the environments' floors, whose default is the epsilon Horgan et al.'s Ape-X gives its most exploring actor.* |
| `--agent.pqn.epsilon-start` | `1.0` | *The chance of a random action at the run's first step, whose default is the one Gallici et al.'s Atari settings start at.* |
| `--agent.pqn.exploration-fraction` | `0.1` | *The share of the run's steps over which each environment's chance of a random action falls linearly from `epsilon_start` to its floor, whose default is the decay of Gallici et al.'s Atari settings.* |
| `--agent.pqn.learning-rate` | `0.00025` | *The step size RAdam takes on every minibatch, held constant across the run, whose default is the learning rate of Gallici et al.'s Atari settings.* |
| `--agent.pqn.max-grad-norm` | `10.0` | *The norm each minibatch's gradient is clipped to, whose default is the maximum gradient norm of Gallici et al.'s Atari settings.* |
| `--agent.pqn.minibatches` | `32` | *The minibatches each epoch splits the rollout into, whose default is the count of Gallici et al.'s Atari settings.* |
| `--agent.pqn.rollout-steps` | `512` | *The steps each environment takes in a rollout, which each update then reads whole, whose default gives 8 environments the 4,096 samples of Gallici et al.'s Atari settings, their 128 environments of 32 steps.* |
| `--agent.pqn.trace-decay` | `0.65` | *The λ that weights each λ-return the network's values are trained toward, whose default is the one of Gallici et al.'s Atari settings.* |
| `--agent.sync-steps` | `1000` | *The environment steps between two copies of the deep Q-network's online network into its target network, whose default follows CleanRL's `dqn_atari.py`.* |
| `--agent.threads` | `none` | *The threads PyTorch spreads each operation on the CPU across, set for the agent's whole process through `torch.set_num_threads` before its networks are built, whose default leaves the count PyTorch chooses.* |
| `--agent.update-steps` | `4` | *The environment steps between two updates of the deep Q-network, whose default is the update frequency Mnih et al. set.* |
| `--agent.warmup-steps` | `50000` | *The environment steps whose transitions the deep Q-network's replay memory gathers before its first update, no fewer than `batch_size`, whose default is the replay start size Mnih et al. set.* |

<!-- /settings:agent -->

[^mnih2015]: Mnih et al. 2015. "Human-level control through deep reinforcement learning." *Nature* 518(7540): 529–533. <https://doi.org/10.1038/nature14236>

[^pleines2025]: Pleines et al. 2025. "Pokémon Red via Reinforcement Learning." *2025 IEEE Conference on Games (CoG)*: 1–8. <https://doi.org/10.1109/cog64752.2025.11114399>

[^vanhasselt2016]: van Hasselt et al. 2016. "Deep Reinforcement Learning with Double Q-Learning." *Proceedings of the AAAI Conference on Artificial Intelligence* 30(1). <https://doi.org/10.1609/aaai.v30i1.10295>

[^gallici2025]: Gallici et al. 2025. "Simplifying Deep Temporal Difference Learning." *International Conference on Learning Representations* 2025: 78148–78190. <https://proceedings.iclr.cc/paper_files/paper/2025/hash/c23f3852601f6dd7f0b39223d031806f-Abstract-Conference.html>

[^horgan2018]: Horgan et al. 2018. "Distributed Prioritized Experience Replay." *International Conference on Learning Representations*. <https://openreview.net/forum?id=H1Dy---0Z>

[^schulman2017]: Schulman et al. 2017. "Proximal Policy Optimization Algorithms." arXiv:1707.06347. <https://arxiv.org/abs/1707.06347>

[^schulman2015]: Schulman et al. 2015. "High-Dimensional Continuous Control Using Generalized Advantage Estimation." arXiv:1506.02438. <https://arxiv.org/abs/1506.02438>
