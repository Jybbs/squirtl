# Curriculum

A run of PQN or PPO can learn the walk to its goal backward, starting its training episodes partway along a demonstration, the shortest episode of an earlier run that reached the same goal, and moving each start back toward Blue's bedroom as the agent succeeds from it. Salimans and Chen[^salimans2018] learn Montezuma's Revenge from a single demonstration this way, and the windows each start is drawn from move as Appendix B of Mhammedi and Cohan[^mhammedi2026] moves them. Every training episode starts in Blue's bedroom unless `--curriculum.demonstration` names a run, and every evaluation episode starts there whatever the training did.

## The Segments

The demonstration splits into segments, each ending at the step whose press first sets one of the flags the reward pays, so on the way to the starter the walk to Oak, the walk into the lab, the wait for Oak to ask, and the choice of the starter each make a segment. Each segment draws its starts from a window of 25 steps reaching back from its latest start, which opens at the segment's end.

## Moving a Window

An episode from a start succeeds once the reward for the flags it sets reaches what the demonstration earned for them from the same step to its segment's end, which ends the episode. Every 32 episodes from a window, the share that succeeded moves it:

- At 20% or more, the window moves back toward the bedroom by between a quarter and three quarters of its span, drawn uniformly
- Below 20%, it moves forward by between half and all of its span

A segment counts as solved once its window has reached Blue's bedroom and 95% of the recent episodes from there succeed, after which no episode starts from it. An episode from a start also truncates after twice the moving average of the lengths of the episodes that succeeded, plus 500 steps.

The drawing below plays a run made up for it over the site's model of the walk to the starter, in which a seeded model of an agent improving with training decides whether each episode succeeds, so it shows how the windows move rather than how fast a real run moves them. The model sets the flag for Oak asking Blue to choose on the press that brings him into the lab behind Oak, where the game sets it only after four text boxes, which leaves the drawing three segments, each lane holding one episode of the batch at its start.

## Playing Back a Start

`squirtl watch` plays an episode that started along a demonstration from the bedroom, playing the demonstration's presses up to its start before the episode's own, while the return it reports counts the episode's own steps alone.

## Settings

The table below is written from the help `squirtl train` prints for each `--curriculum.` setting, and `mise write` rewrites it.

<!-- settings:curriculum -->

| **Flag** | **Default** | **What It Sets** |
|---|---|---|
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

<!-- /settings:curriculum -->

[^salimans2018]: Salimans and Chen 2018. "Learning Montezuma's Revenge from a Single Demonstration." arXiv:1812.03381. <https://arxiv.org/abs/1812.03381>

[^mhammedi2026]: Mhammedi and Cohan 2026. "Decoupling Exploration and Policy Optimization: Uncertainty Guided Tree Search for Hard Exploration." arXiv:2603.22273v4. <https://arxiv.org/abs/2603.22273v4>
