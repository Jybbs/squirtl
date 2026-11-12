<!-- help -->

# `squirtl search`

Searches for a path from Blue's bedroom to `--environment.goal` over saved states, across `--search.workers` processes, ending once a particle sets the goal or the presses reach the run's `--steps`, logging a line per iteration above a progress bar.

The run writes its record, a line per iteration, and a checkpoint into a directory of its own under `data/runs/`, which the command prints once the search ends, and the path to the goal, once it finds one, as an episode reaching it, which `squirtl watch` plays and `--curriculum.demonstration` reads. An interrupt, a termination signal, or `squirtl stop` ends the search at the end of its iteration with a checkpoint and exits 0, and a second interrupt ends it at once on the last checkpoint and exits 130.

Each of these exits 1 before any directory is made:

- A `--resume` directory holding no search or no checkpoint
- A `--resume` directory holding a training run
- A checkpoint damaged, already holding the goal or the run's steps, or differing from the search the run's settings build
- An iteration log ending short of that checkpoint
- A cartridge the emulator refuses
- A working directory no git clone holds

```console
squirtl search [OPTIONS]
```

<!-- /help -->

A search starts every particle on the state Blue's bedroom leaves, presses each rollout from a node it saved, and keeps the path of the particle reaching the most reward. Once a particle sets the goal, the path it took becomes the one episode in the search's `episodes.jsonl`, so `squirtl watch` plays it and `--curriculum.demonstration` takes the directory as a demonstration.

<!-- settings -->

## Settings

| **Flag** | **Default** | **What It Sets** |
|---|---|---|
| `--resume` | `none` | *The directory of a stopped search to continue from its last checkpoint, under the settings that search recorded.* |
| `--agent.algorithm` | `dqn` | *The agent the run trains, the deep Q-network, PQN, or PPO.* |
| `--agent.batch-size` | `32` | *The transitions each update of the deep Q-network draws from replay memory, whose default follows Mnih et al.* |
| `--agent.capacity` | `100000` | *The slots the deep Q-network's replay memory holds before overwriting the oldest, four per reset observation and one per step, whose default takes 606 MB for a 72 by 80 frame, a 48 by 48 grid, and a flag for each member of `Event`, the grid and the flags packed eight cells to a byte.* |
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
| `--agent.pqn.epsilon-end` | `0.001` | *The chance of a random action once exploration has annealed, whose default is the one Gallici et al.'s Atari settings finish at.* |
| `--agent.pqn.epsilon-start` | `1.0` | *The chance of a random action at the run's first step, whose default is the one Gallici et al.'s Atari settings start at.* |
| `--agent.pqn.exploration-fraction` | `0.1` | *The share of the run's steps over which the chance of a random action falls linearly from `epsilon_start` to `epsilon_end`, whose default is the decay of Gallici et al.'s Atari settings.* |
| `--agent.pqn.learning-rate` | `0.00025` | *The step size RAdam takes on every minibatch, held constant across the run, whose default is the learning rate of Gallici et al.'s Atari settings.* |
| `--agent.pqn.max-grad-norm` | `10.0` | *The norm each minibatch's gradient is clipped to, whose default is the maximum gradient norm of Gallici et al.'s Atari settings.* |
| `--agent.pqn.minibatches` | `32` | *The minibatches each epoch splits the rollout into, whose default is the count of Gallici et al.'s Atari settings.* |
| `--agent.pqn.rollout-steps` | `512` | *The steps each environment takes in a rollout, which each update then reads whole, whose default gives 8 environments the 4,096 samples of Gallici et al.'s Atari settings, their 128 environments of 32 steps.* |
| `--agent.pqn.trace-decay` | `0.65` | *The λ that weights each λ-return the network's values are trained toward, whose default is the one of Gallici et al.'s Atari settings.* |
| `--agent.sync-steps` | `1000` | *The environment steps between two copies of the deep Q-network's online network into its target network, whose default follows CleanRL's `dqn_atari.py`.* |
| `--agent.threads` | `none` | *The threads PyTorch spreads each operation on the CPU across, set for the agent's whole process through `torch.set_num_threads` before its networks are built, whose default leaves the count PyTorch chooses.* |
| `--agent.update-steps` | `4` | *The environment steps between two updates of the deep Q-network, whose default is the update frequency Mnih et al. set.* |
| `--agent.warmup-steps` | `50000` | *The environment steps whose transitions the deep Q-network's replay memory gathers before its first update, no fewer than `batch_size`, whose default is the replay start size Mnih et al. set.* |
| `--checkpoint-steps` | `250000` | *The environment steps between checkpoints, each written at the first episode end, or the end of a rollout's update for PQN and PPO, reaching a multiple of them, whose default is the 250,000 steps of each iteration Dopamine's DQN checkpoints after.* |
| `--curriculum.back` | `0.25, 0.75` | *The least and the most a window moves back, each a multiple of `window`, between which each move draws uniformly, whose default is the decrease multipliers of Mhammedi and Cohan's Table 8.* |
| `--curriculum.buffer` | `500` | *The steps an episode from a start takes beyond `multiplier` times the moving average of successful lengths before it truncates, whose default is the rollout length buffer of Mhammedi and Cohan's Table 8.* |
| `--curriculum.completion` | `0.95` | *The share of the recent episodes from a window reaching Blue's bedroom that have to succeed before its segment counts as solved, whose default is the completion threshold of Mhammedi and Cohan's Table 8.* |
| `--curriculum.demonstration` | `none` | *The directory of the run whose shortest episode reaching the goal each training episode starts along, a run ending its episodes at the same goal, or `None` to start every episode in Blue's bedroom.* |
| `--curriculum.forward` | `0.5, 1.0` | *The least and the most a window moves forward, each a multiple of `window`, between which each move draws uniformly, whose default is the increase multipliers of Mhammedi and Cohan's Table 8.* |
| `--curriculum.multiplier` | `2.0` | *The multiple of the moving average of successful lengths an episode from a start takes before `buffer` and then truncates, whose default is the early termination multiplier of Mhammedi and Cohan's Table 8.* |
| `--curriculum.recent` | `32` | *The episodes from a window whose share of successes moves it, after which the count starts again, whose default is the minimum rollouts for an update of Mhammedi and Cohan's Table 8.* |
| `--curriculum.required` | `0.2` | *The share of the recent episodes from a window that have to succeed for it to move back, where a smaller share moves it forward, whose default is the required success rate of Mhammedi and Cohan's Table 8.* |
| `--curriculum.smoothing` | `0.9` | *The weight the moving average of successful lengths gives each new length, the smoothing constant of single exponential smoothing in section 6.4.3.1 of the NIST/SEMATECH e-Handbook of Statistical Methods, whose default is the smoothing factor of Mhammedi and Cohan's Table 8.* |
| `--curriculum.tolerance` | `0.0` | *The reward an episode from a start may fall short of the demonstration's from the same step and still succeed, whose default is the failure reward tolerance of Mhammedi and Cohan's Table 8.* |
| `--curriculum.window` | `25` | *The steps of the demonstration each segment's window spans back from its latest start, whose default is the start delta window of Mhammedi and Cohan's Table 8.* |
| `--emulator.cartridge` | `data/rom.gb` | *The file holding the user's own ROM of the English Pokémon Blue, refused unless its SHA-1 is the one pret/pokered lists.* |
| `--emulator.hold` | `2` | *The frames a press holds its button down, since pret/pokered's `OverworldLoop` calls `DelayFrame` twice before each `JoypadOverworld`, so the overworld reads the joypad every second frame and misses a press held for one frame that falls between two reads.* |
| `--emulator.open-window` | `false` | *Whether PyBoy draws the last frame of each step in an SDL2 window, pacing the steps at sixty a second, where otherwise a run draws nothing and advances as fast as the machine allows.* |
| `--environment.frame-shape` | `72, 80` | *The height and width in pixels each frame shrinks to, each dividing the screen's own, whose default is the half-resolution grayscale screen Pleines et al. observe.* |
| `--environment.frame-stack` | `4` | *The frames each observation stacks, the newest last, whose default follows Mnih et al.* |
| `--environment.frames-per-step` | `17` | *The frames a step advances from its press, by default the fewest under which a direction pressed on open ground moves the player one square whichever frame the press lands on.* |
| `--environment.goal` | `event-got-starter` | *The flag whose first setting ends an episode, each flag `Event` declares before it paying the milestone, whose default is the starter and whose farthest is the Pokédex, since the old man lying across Viridian City's road north turns Blue back until `EVENT_GOT_POKEDEX` is set, as pret/pokered's `scripts/ViridianCity.asm` holds.* |
| `--environment.grid-size` | `48` | *The side in squares of the grid of reached positions centered on the player, by default one square per cell of the 48 by 48 crop Pleines et al. observe.* |
| `--environment.max-episode-steps` | `10240` | *The steps after which `TimeLimit` truncates an episode, by default the budget Pleines et al. start each episode with.* |
| `--evaluation.environments` | *the machine's* | *The environments an evaluation plays its episodes across in parallel, each in a worker process of its own, which defaults to the CPUs the process may use.* |
| `--evaluation.episodes` | `30` | *The episodes each evaluation plays of the agent and of the random baseline, whose default follows Mnih et al.* |
| `--evaluation.epsilon` | `0.05` | *The chance of a random action at each step of an evaluation episode of the deep Q-network or of PQN, whose default follows Mnih et al. PPO takes its most likely action at every step.* |
| `--evaluation-steps` | `250000` | *The environment steps between the evaluations a run plays, each where an episode end, the end of a rollout's update for PQN and PPO, or the run's last step first reaches a multiple of them, whose default is the 250,000 steps of each iteration Dopamine's DQN evaluates after.* |
| `--reward.goal` | `0.35` | *The reward the step first setting the run's goal earns, which has to be the largest term.* |
| `--reward.milestone` | `0.1` | *The reward a step earns for each flag on the way to the goal it first sets.* |
| `--reward.novelty` | `0.00025` | *The reward a step earns for reaching a position the episode has not reached before, whose default is a 400th of the default milestone, the ratio Pleines et al. pay one new coordinate against one completed event.* |
| `--search.batch-size` | `128` | *The frame stacks each update of the predictor draws, whose default follows Mhammedi and Cohan's Appendix A.3.* |
| `--search.capacity` | `512000` | *The frames replay memory holds for the predictor, one per slot, about 2.95 GB at the default frame shape, whose default follows Mhammedi and Cohan's Appendix A.3.* |
| `--search.epsilon` | `0.2` | *The chance a press takes a random action in place of the one its rollout holds, whose default follows Mhammedi and Cohan's Appendix A.2.* |
| `--search.groups` | `4` | *The groups of particles the search evolves, Mhammedi and Cohan's M.* |
| `--search.inner-steps` | `5, 15` | *The fewest and the most presses of one rollout, Mhammedi and Cohan's range of T.* |
| `--search.learning-rate` | `0.0003` | *The step size Adam takes on the predictor, whose default follows Mhammedi and Cohan's Appendix A.3.* |
| `--search.outer-steps` | `10, 20` | *The fewest and the most rollouts each particle plays in one iteration, Mhammedi and Cohan's range of K.* |
| `--search.particles` | `32` | *The particles each group holds, Mhammedi and Cohan's N.* |
| `--search.rollback` | `1, 3` | *The fewest and the most generations a particle moves up the tree once every particle of its group is dead, Mhammedi and Cohan's range of k.* |
| `--search.update-steps` | `44` | *The presses between updates of the predictor, whose default is the ratio of Mhammedi and Cohan's Table 6, 2.28 million updates over 400 million frames at their action repeat of 4.* |
| `--search.workers` | *the machine's* | *The worker processes the rollouts run across, which defaults to the CPUs the process may use.* |
| `--seed` | `1` | *The seed every random draw in the run derives from, whose default follows CleanRL's `dqn_atari.py`.* |
| `--steps` | `2500000` | *The environment steps the run takes, a run of PQN or PPO going on to the end of the rollout that reaches them, whose default is ten of the 250,000-step iterations Dopamine's DQN evaluates after.* |

<!-- /settings -->
