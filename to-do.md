- Look into `boost` as a way to bind C++ to Python
- Introduce chaos in Agent.act, so there are opportunities for "revelations"
- NP-Complete: traveling salesman to major checkpoint
- Refactor for conciseness in all Classes

#### Ideas for Reward Structure
1. Instead of +1000 and a -1 for each action, make the final event reward `num_episodes` - `num_actions`
2. After optimization with PCA (of ndarrays passed via PyBoy), introduce a more encompassing penalty for backtracking (e.g. a backtrack is not just a copy of an exact state, but a copy of a PCA-optimized state)
3. Tinker with the reward structure to try to encourage epxloitation (e.g. quick progress to the final event) over exploration for the sake of exploration