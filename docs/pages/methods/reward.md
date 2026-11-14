# Reward

The reward pays a step for what it adds to its episode, a little for each square Blue reaches for the first time in the episode and far more for each milestone on the way to the run's goal, with the goal itself the largest payment. Every figure it reads comes from the game's memory at the addresses [pret/pokered](https://github.com/pret/pokered) names, so the reward reads nothing off the screen.

## The Bytes It Reads

`wCurMap` holds the map Blue stands on, `wYCoord` and `wXCoord` his row and column on that map, and `wEventFlags` the first byte of the event flags, one bit per event the game has seen. A search reads more of them. `wPartyCount` and `wPartyMons` hold the HP left in Blue's party, and in a battle, which `wIsInBattle` marks, `wPlayerMonNumber` names the Pokémon he has sent out and `wBattleMon` holds its HP, which the party's copy lags behind until the turn's end. `wTileMap` holds the tiles the game last drew beneath the sprites. A search marks a rollout dead where it leaves the flags, the position, and those tiles as it found them, and where Blue's last Pokémon faints anywhere but in Oak's lab before his battle with the rival there ends, the rollout stopping at the faint itself rather than at the blackout that follows, per [`squirtl search`](../commands/search.md). The table below is written from the addresses `Symbol` declares, and `mise write` rewrites it.

<!-- symbols -->

| **Address** | **Label** |
|---|---|
| `0xC3A0` | `wTileMap` |
| `0xCC2F` | `wPlayerMonNumber` |
| `0xD014` | `wBattleMon` |
| `0xD057` | `wIsInBattle` |
| `0xD163` | `wPartyCount` |
| `0xD16B` | `wPartyMons` |
| `0xD35E` | `wCurMap` |
| `0xD361` | `wYCoord` |
| `0xD362` | `wXCoord` |
| `0xD747` | `wEventFlags` |

<!-- /symbols -->

The map, the row, and the column together name a position, and the event flags hold the milestones, each a bit of `wEventFlags` at the index pret/pokered's `constants/event_constants.asm` gives it. In the order Blue reaches them, `EVENT_OAK_APPEARED_IN_PALLET` sets once Oak stops Blue at the north edge of Pallet Town, `EVENT_FOLLOWED_OAK_INTO_LAB` once Blue follows Oak into his lab, `EVENT_OAK_ASKED_TO_CHOOSE_MON` once Oak asks Blue to choose, `EVENT_GOT_STARTER` once Blue takes his starter, `EVENT_BATTLED_RIVAL_IN_OAKS_LAB` once the rival's first battle ends, `EVENT_GOT_OAKS_PARCEL` once the clerk of the Viridian City Poké Mart hands Blue Oak's parcel, and `EVENT_GOT_POKEDEX` once Oak gives Blue the Pokédex for it. A run's `--environment.goal` names the flag whose first setting ends its episodes, the starter by default and the Pokédex at the farthest, since the old man lying across Viridian City's road north turns Blue back until `EVENT_GOT_POKEDEX` is set. Each flag before the goal pays `--reward.milestone`, and those past it pay nothing. The table below is written from the flags `Event` declares, in the order the opening sets them, and `mise write` rewrites it.

<!-- events -->

| **Event** | **Index** |
|---|---|
| `EVENT_OAK_APPEARED_IN_PALLET` | `0x27` |
| `EVENT_FOLLOWED_OAK_INTO_LAB` | `0x00` |
| `EVENT_OAK_ASKED_TO_CHOOSE_MON` | `0x21` |
| `EVENT_GOT_STARTER` | `0x22` |
| `EVENT_BATTLED_RIVAL_IN_OAKS_LAB` | `0x23` |
| `EVENT_GOT_OAKS_PARCEL` | `0x39` |
| `EVENT_GOT_POKEDEX` | `0x25` |

<!-- /events -->

## The Payment

The reward of a step from state $`s`$ through press $`a`$ to state $`s'`$ sums three terms:

```math
R(s, a, s') = 0.00025 \cdot \mathbb{1}[p' \notin P] + 0.1 \cdot |M' \setminus M| + 0.35 \cdot \mathbb{1}[g' \land \lnot g]
```

Here $`p'`$ is the position the step ends on and $`P`$ every position the episode reached before it, $`M`$ and $`M'`$ are the flags preceding the run's goal that are set before and after the step, and $`g`$ and $`g'`$ are whether the goal is set before and after it. A new position pays a 400th of a milestone, the ratio Pleines et al.[^pleines2025] pay one new coordinate against one completed event, and a run's settings are refused where one step reaching a new position and first setting every flag up to its goal at once would earn more than 1, the bound Mnih et al.[^mnih2015] clip each reward to. At the Pokédex, the six milestones before it, the goal, and a new position total 0.95025.

## Settings

The table below is written from the help `squirtl train` prints for each `--reward.` setting, and `mise write` rewrites it.

<!-- settings:reward -->

| **Flag** | **Default** | **What It Sets** |
|---|---|---|
| `--reward.goal` | `0.35` | *The reward the step first setting the run's goal earns, which has to be the largest term.* |
| `--reward.milestone` | `0.1` | *The reward a step earns for each flag on the way to the goal it first sets.* |
| `--reward.novelty` | `0.00025` | *The reward a step earns for reaching a position the episode has not reached before, whose default is a 400th of the default milestone, the ratio Pleines et al. pay one new coordinate against one completed event.* |

<!-- /settings:reward -->

[^pleines2025]: Pleines et al. 2025. "Pokémon Red via Reinforcement Learning." *2025 IEEE Conference on Games (CoG)*: 1–8. <https://doi.org/10.1109/cog64752.2025.11114399>

[^mnih2015]: Mnih et al. 2015. "Human-level control through deep reinforcement learning." *Nature* 518(7540): 529–533. <https://doi.org/10.1038/nature14236>
