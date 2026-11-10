# Reward

The reward pays a step for what it adds to its episode, a little for each square Blue reaches for the first time in the episode and far more for each milestone on the way to the starter, with the starter itself the largest payment. Every figure it reads comes from the game's memory at the addresses [pret/pokered](https://github.com/pret/pokered) names, so the reward reads nothing off the screen.

## The Bytes It Reads

`wCurMap` holds the map Blue stands on, `wYCoord` and `wXCoord` his row and column on that map, and `wEventFlags` the first byte of the event flags, one bit per event the game has seen. The table below is written from the addresses `Symbol` declares, and `mise write` rewrites it.

<!-- symbols -->

| **Address** | **Label** |
|---|---|
| `0xD35E` | `wCurMap` |
| `0xD361` | `wYCoord` |
| `0xD362` | `wXCoord` |
| `0xD747` | `wEventFlags` |

<!-- /symbols -->

The map, the row, and the column together name a position, and the event flags hold the milestones, each a bit of `wEventFlags` at the index pret/pokered's `constants/event_constants.asm` gives it. In the order Blue reaches them, `EVENT_OAK_APPEARED_IN_PALLET` sets once Oak stops Blue at the north edge of Pallet Town, `EVENT_FOLLOWED_OAK_INTO_LAB` once Blue follows Oak into his lab, `EVENT_OAK_ASKED_TO_CHOOSE_MON` once Oak asks Blue to choose, and `EVENT_GOT_STARTER` once Blue takes his starter, which ends the episode. The table below is written from the flags `Event` declares, each beside the setting holding what a step earns for first setting it, and `mise write` rewrites it.

<!-- events -->

| **Event** | **Index** | **Pays** |
|---|---|---|
| `EVENT_FOLLOWED_OAK_INTO_LAB` | `0x00` | `--reward.milestone` |
| `EVENT_OAK_ASKED_TO_CHOOSE_MON` | `0x21` | `--reward.milestone` |
| `EVENT_GOT_STARTER` | `0x22` | `--reward.starter` |
| `EVENT_OAK_APPEARED_IN_PALLET` | `0x27` | `--reward.milestone` |

<!-- /events -->

## The Payment

The reward of a step from state $`s`$ through press $`a`$ to state $`s'`$ sums three terms:

```math
R(s, a, s') = 0.00025 \cdot \mathbb{1}[p' \notin P] + 0.1 \cdot |M' \setminus M| + 0.6 \cdot \mathbb{1}[g' \land \lnot g]
```

Here $`p'`$ is the position the step ends on and $`P`$ every position the episode reached before it, $`M`$ and $`M'`$ are the milestone flags set before and after the step, and $`g`$ and $`g'`$ are whether `EVENT_GOT_STARTER` is set before and after it. A new position pays a 400th of a milestone, the ratio Pleines et al.[^pleines2025] pay one new coordinate against one completed event, and every step's reward stays within 1, the bound Mnih et al.[^mnih2015] clip each reward to.

## Settings

The table below is written from the help `squirtl train` prints for each `--reward.` setting, and `mise write` rewrites it.

<!-- settings:reward -->

| **Flag** | **Default** | **What It Sets** |
|---|---|---|
| `--reward.milestone` | `0.1` | *The reward a step earns for each milestone on the way to the starter whose flag it first sets.* |
| `--reward.novelty` | `0.00025` | *The reward a step earns for reaching a position the episode has not reached before, whose default is a 400th of the default milestone, the ratio Pleines et al. pay one new coordinate against one completed event.* |
| `--reward.starter` | `0.6` | *The reward the step first setting `EVENT_GOT_STARTER` earns, which has to be the largest term.* |

<!-- /settings:reward -->

[^pleines2025]: Pleines et al. 2025. "Pokémon Red via Reinforcement Learning." *2025 IEEE Conference on Games (CoG)*: 1–8. <https://doi.org/10.1109/cog64752.2025.11114399>

[^mnih2015]: Mnih et al. 2015. "Human-level control through deep reinforcement learning." *Nature* 518(7540): 529–533. <https://doi.org/10.1038/nature14236>
