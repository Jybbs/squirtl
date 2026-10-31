# SquiRtL

*A deep Q-network that learns the walk to Oak’s lab.*

*SquiRtL* trains an agent to play Pokémon Blue from the screen alone. A deep Q-network reads the frames the PyBoy emulator draws, presses one of the Game Boy's buttons each step, and learns from a reward read out of the game's memory, until Blue walks from his bedroom to Oak's lab and chooses his starter. Each part of the story below plays on a model of the game's first rooms in the page, so it runs with no emulator and no ROM.

## The Reward

Every step of an episode pays a little for each position Blue has not reached before and far more for each milestone on the way to the starter, which ends the episode.

## What the Network Sees

The network never reads where Blue stands, reading instead the last four frames of the screen shrunk to gray, the squares he has reached around him, and four flags for the moments that pay.

## Learning in the Page

Training spreads value back from where an episode pays, square by square, so each walk from Blue's door after more episodes spends fewer presses at random and reaches Pallet Town's north edge, where Oak appears, sooner. Here a small table of values, trained in the page over a model of Pallet Town, stands in for the deep Q-network, which trains only through `squirtl train`.

## Against Random Presses

Each run is evaluated beside random presses under the same seeds, counting how many of each player's episodes reach the starter and how many steps each takes to get there. Here the agent's part goes to a player that walks the shortest way to the starter and presses at random as often as an evaluation does, so the race shows the shape of an evaluation rather than the result of a trained run.
