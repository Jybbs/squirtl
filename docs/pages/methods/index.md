# Methods

*SquiRtL* learns to walk Blue from his bedroom to Oak's lab and to choose a starter, reading nothing but the screen and a reward drawn from the game's memory. Each episode starts in Blue's bedroom, where he stands once the intro is played through, and ends when he receives his starter or when the step budget runs out.

## The Parts of a Run

A run joins four parts, each set out on a page of its own:

- The [environment](./environment.md) presses one button a step, advances the game 17 frames, and returns the screens the agent reads
- The [reward](./reward.md) reads the game's memory after each step and pays for a square not reached before and for each milestone on the way to the starter
- The [agents](./agents.md) choose each press and learn from what it paid, whether the deep Q-network, PQN, or PPO
- The [curriculum](./curriculum.md) starts a training episode partway along a demonstration and moves its start back toward the bedroom as the agent succeeds

The [evaluation](./evaluation.md) then plays each trained agent from the bedroom beside random presses under the same seeds.

## Prior Work on the Game

Pleines et al.[^pleines2025] train PPO on Pokémon Red from the screen, a crop of the positions reached, and the game's event flags, and many of the defaults here follow their settings. Peter Whidden's [PokemonRedExperiments](https://github.com/PWhiddy/PokemonRedExperiments) trains PPO on the same game, paying its agent for reaching places it has not seen.

[^pleines2025]: Pleines et al. 2025. "Pokémon Red via Reinforcement Learning." *2025 IEEE Conference on Games (CoG)*: 1–8. <https://doi.org/10.1109/cog64752.2025.11114399>
