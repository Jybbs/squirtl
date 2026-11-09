# Reward

The reward pays a step for what it adds to its episode, a little for each square Blue reaches for the first time in the episode and far more for each milestone on the way to the starter, with the starter itself the largest payment. Every figure it reads comes from the game's memory at the addresses [pret/pokered](https://github.com/pret/pokered) names, so the reward reads nothing off the screen.

## The Bytes It Reads

| **Address** | **Symbol** | **What It Holds** |
|---|---|---|
| `0xD35E` | `wCurMap` | *The map Blue stands on* |
| `0xD361` | `wYCoord` | *Blue's row on that map* |
| `0xD362` | `wXCoord` | *Blue's column on that map* |
| `0xD747` | `wEventFlags` | *The first byte of the event flags, one bit per event the game has seen* |

The map, the row, and the column together name a position, and the event flags hold the milestones, each a bit of `wEventFlags` at the index pret/pokered's `constants/event_constants.asm` gives it:

| **Event** | **Index** | **Pays** |
|---|---|---|
| `EVENT_OAK_APPEARED_IN_PALLET` | `0x27` | *A milestone, once Oak stops Blue at the north edge of Pallet Town* |
| `EVENT_FOLLOWED_OAK_INTO_LAB` | `0x00` | *A milestone, once Blue follows Oak into his lab* |
| `EVENT_OAK_ASKED_TO_CHOOSE_MON` | `0x21` | *A milestone, once Oak asks Blue to choose* |
| `EVENT_GOT_STARTER` | `0x22` | *The starter, which ends the episode* |

## The Payment

The reward of a step from state $`s`$ through press $`a`$ to state $`s'`$ sums three terms:

```math
R(s, a, s') = 0.00025 \cdot \mathbb{1}[p' \notin P] + 0.1 \cdot |M' \setminus M| + 0.6 \cdot \mathbb{1}[g' \land \lnot g]
```

Here $`p'`$ is the position the step ends on and $`P`$ every position the episode reached before it, $`M`$ and $`M'`$ are the milestone flags set before and after the step, and $`g`$ and $`g'`$ are whether `EVENT_GOT_STARTER` is set before and after it. A new position pays a 400th of a milestone, the ratio Pleines et al.[^pleines2025] pay one new coordinate against one completed event, and every step's reward stays within 1, the bound Mnih et al.[^mnih2015] clip each reward to.

## Settings

<!-- settings:reward -->

| **Flag** | **Default** | **What It Sets** |
|---|---|---|
| `--reward.milestone` | `0.1` | *The reward a step earns for each milestone on the way to the starter whose flag it first sets.* |
| `--reward.novelty` | `0.00025` | *The reward a step earns for reaching a position the episode has not reached before, whose default is a 400th of the default milestone, the ratio Pleines et al. pay one new coordinate against one completed event.* |
| `--reward.starter` | `0.6` | *The reward the step first setting `EVENT_GOT_STARTER` earns, which has to be the largest term.* |

<!-- /settings:reward -->

[^pleines2025]: Pleines et al. 2025. "Pokémon Red via Reinforcement Learning." *2025 IEEE Conference on Games (CoG)*: 1–8. <https://doi.org/10.1109/cog64752.2025.11114399>

[^mnih2015]: Mnih et al. 2015. "Human-level control through deep reinforcement learning." *Nature* 518(7540): 529–533. <https://doi.org/10.1038/nature14236>
