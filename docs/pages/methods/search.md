# Search

`squirtl search` finds a way from Blue's bedroom to the run's goal without training anything, and its path becomes the demonstration the [curriculum](./curriculum.md) starts its episodes along. It plays copies of the game forward from states it saved, keeps the copies reaching the most, and moves the rest onto them, following Mhammedi and Cohan's search[^mhammedi2026], which builds on the go-with-the-winners algorithms of Aldous and Vazirani[^aldous1994]. Once a copy sets the goal's flag, by default when Blue receives his starter, the presses along its lineage from the bedroom and the `timer_div` its reset wrote into `DIV` are the demonstration, holding no frame or saved state from the game.

## Groups and Winners

The search splits its copies into groups, `--search.groups` of them with `--search.particles` copies each. A copy plays a **rollout** from a node of the search's tree, holding one button drawn for the rollout and pressing a random one in its place at `--search.epsilon` a press. The rollout stops early at the press setting a flag the reward pays, whereas a new square leaves it playing. Each rollout that survives adds a node to the tree, holding its parent and the presses reaching it, and the tree keeps a saved state only for a node a copy moves to.

A group ranks its copies on the total the [reward](./reward.md) pays their lineage from the bedroom, each new square and each flag included, and then on the uncertainty random network distillation measures on their frames. Its highest-ranked copy is its **winner**, and each copy that dies moves to the winner's node, so the group goes on from the states that reached the most. Once every copy of a group dies, each moves up the tree instead, by between one and three generations under the default `--search.rollback`. An iteration plays between ten and twenty rollouts from every copy under the default `--search.outer_steps`. At its end every group moves to its winner, and a group whose winner ranks below the best winner on reward moves to the best one. The tree then drops every saved state on no lineage of the nodes the copies stand on.

## Dead Rollouts

A rollout is dead where Blue blacks out, or where it sets no flag, reaches no new square, and ends on the screen and the square it began on, so a rollout that only walks into a wall or turns in place leaves nothing to keep. A rollout that advances a text box without moving Blue changes the screen and survives.

## Eight Copies of the Game

The drawing below plays a small search over the site's model of the walk to the starter, the model the curriculum's drawing runs on. Its sizes are made up for it, two groups of four copies where `--search.groups` defaults to 4 and `--search.particles` to 32, and rollouts of at most ten presses where `--search.inner_steps` draws between five and fifteen. Each iteration of the drawing plays one rollout for every copy and then moves each group's copies to its winner, or one node up the tree where all of them die, and both groups move to the better winner every fourth iteration. The drawing's uncertainty is how rarely the search has stood on a rollout's last square, a stand-in for the random network distillation the search runs over the frames, and a rollout counts as dead where it ends on the screen, the square, and the reward it began on.

The copy that first chooses a starter ends the search, and the slider's last position shows its demonstration's length beside the copies as they stood when it did.

[^mhammedi2026]: Mhammedi and Cohan 2026. "Decoupling Exploration and Policy Optimization: Uncertainty Guided Tree Search for Hard Exploration." arXiv:2603.22273v4. <https://arxiv.org/abs/2603.22273v4>

[^aldous1994]: Aldous and Vazirani 1994. "'Go with the winners' algorithms." *Proceedings 35th Annual Symposium on Foundations of Computer Science*: 492–501. <https://doi.org/10.1109/sfcs.1994.365742>
