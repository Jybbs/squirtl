- Look into `boost` as a way to bind C++ to Python

#### Ideas
1. After optimization with PCA (of ndarrays passed via PyBoy), introduce a more encompassing penalty for backtracking (e.g. a backtrack is not just a copy of an exact state, but a copy of a PCA-optimized state)
2. Should frame-skip be in the action space?
3. rcParams for final plot

#### Conciseness
1. Ineffective logic seems broken. We got 1000 ineffective actions in test run, when some of those should be considered "new" and effective