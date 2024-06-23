- Look into `boost` as a way to bind C++ to Python
- Introduce chaos in Agent.act, so there are opportunities for "revelations"
- NP-Complete: traveling salesman to major checkpoint
- Refactor for conciseness in all Classes

#### Ideas for Reward Structure
1. After optimization with PCA (of ndarrays passed via PyBoy), introduce a more encompassing penalty for backtracking (e.g. a backtrack is not just a copy of an exact state, but a copy of a PCA-optimized state)