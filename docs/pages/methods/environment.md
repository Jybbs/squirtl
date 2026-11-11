# Environment

The environment is the game from Blue's bedroom to the run's goal as a [Gymnasium](https://gymnasium.farama.org/) `Env`, run on the [PyBoy](https://docs.pyboy.dk/) emulator over the user's own ROM. Before the first step of a run, it plays through the intro, choosing BLUE and RED on the naming screens, and saves the state Blue's bedroom opens on. Each episode resets to that state and writes a value its seed draws into the divider register `DIV`, which pret/pokered's `Random_` in `engine/math/random.asm` reads, so episodes under different seeds meet different draws of the game's randomness.

## A Step

Each step makes one press and advances the game 17 frames, about 0.28 seconds of play at the Game Boy's 59.7 frames a second. A press holds its button down for the first 2 of those frames, because [pret/pokered](https://github.com/pret/pokered)'s `OverworldLoop` calls `DelayFrame` twice before each `JoypadOverworld`, so the overworld reads the joypad every second frame and misses a press held for one frame that falls between two reads. Seventeen is the fewest frames under which a direction pressed on open ground moves Blue one square whichever frame the press lands on.

A press of a direction Blue is not already facing from rest turns him in place without a step, as `OverworldLoop` in pret/pokered's `home/overworld.asm` sets a new facing before it moves him, so the step after a turn is the one that moves him.

## The Presses

The agent chooses among seven actions each step, no press, A, B, and the four directions, since no step on the way to the Pokédex takes START or SELECT.

## What the Agent Sees

The agent never reads where Blue stands. Each observation holds three entries:

- The last four frames of the screen in gray, each shrunk to 72 by 80 pixels by averaging the block of pixels each cell covers, the half-resolution screen Pleines et al.[^pleines2025] observe
- A grid of 48 by 48 squares centered on Blue, marking each square of the current map the episode has reached, the crop Pleines et al. observe
- A flag for each event `Event` declares, from Oak appearing in Pallet Town to the Pokédex, set once the game sets it

## The End of an Episode

An episode terminates on the step first setting the run's `--environment.goal`, by default once Blue receives his starter, and it truncates after 10,240 steps, the budget Pleines et al. start each episode with. A truncated episode never reached a state the game marks as final, so each agent keeps bootstrapping from the value of the state a truncated step reaches, as Pardo et al.[^pardo2018] set out for a limit on time the agent does not observe.

## Settings

The table below is written from the help `squirtl train` prints for each `--environment.` setting, and `mise write` rewrites it.

<!-- settings:environment -->

| **Flag** | **Default** | **What It Sets** |
|---|---|---|
| `--environment.frame-shape` | `72, 80` | *The height and width in pixels each frame shrinks to, each dividing the screen's own, whose default is the half-resolution grayscale screen Pleines et al. observe.* |
| `--environment.frame-stack` | `4` | *The frames each observation stacks, the newest last, whose default follows Mnih et al.* |
| `--environment.frames-per-step` | `17` | *The frames a step advances from its press, by default the fewest under which a direction pressed on open ground moves the player one square whichever frame the press lands on.* |
| `--environment.goal` | `event-got-starter` | *The flag whose first setting ends an episode, each flag `Event` declares before it paying the milestone, whose default is the starter and whose farthest is the Pokédex, since the old man lying across Viridian City's road north turns Blue back until `EVENT_GOT_POKEDEX` is set, as pret/pokered's `scripts/ViridianCity.asm` holds.* |
| `--environment.grid-size` | `48` | *The side in squares of the grid of reached positions centered on the player, by default one square per cell of the 48 by 48 crop Pleines et al. observe.* |
| `--environment.max-episode-steps` | `10240` | *The steps after which `TimeLimit` truncates an episode, by default the budget Pleines et al. start each episode with.* |

<!-- /settings:environment -->

The table below is written from the help `squirtl train` prints for each `--emulator.` setting, and `mise write` rewrites it.

<!-- settings:emulator -->

| **Flag** | **Default** | **What It Sets** |
|---|---|---|
| `--emulator.cartridge` | `data/rom.gb` | *The file holding the user's own ROM of the English Pokémon Blue, refused unless its SHA-1 is the one pret/pokered lists.* |
| `--emulator.hold` | `2` | *The frames a press holds its button down, since pret/pokered's `OverworldLoop` calls `DelayFrame` twice before each `JoypadOverworld`, so the overworld reads the joypad every second frame and misses a press held for one frame that falls between two reads.* |
| `--emulator.open-window` | `false` | *Whether PyBoy draws the last frame of each step in an SDL2 window, pacing the steps at sixty a second, where otherwise a run draws nothing and advances as fast as the machine allows.* |

<!-- /settings:emulator -->

[^pleines2025]: Pleines et al. 2025. "Pokémon Red via Reinforcement Learning." *2025 IEEE Conference on Games (CoG)*: 1–8. <https://doi.org/10.1109/cog64752.2025.11114399>

[^pardo2018]: Pardo et al. 2018. "Time Limits in Reinforcement Learning." *Proceedings of the 35th International Conference on Machine Learning*, PMLR 80: 4045–4054. <https://proceedings.mlr.press/v80/pardo18a.html>
