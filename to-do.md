- Look into `boost` as a way to bind C++ to Python

#### Ideas
1. After optimization with PCA (of ndarrays passed via PyBoy), introduce a more encompassing penalty for backtracking (e.g. a backtrack is not just a copy of an exact state, but a copy of a PCA-optimized state)
2. Should frame-skip be in the action space?
3. rcParams for final plot

#### Conciseness
1. Can we better handle common pathing, so that pathlib and os aren't needed in multiple classes? (e.g. can we just find the home path through settings and then reliably create subfolders off of it afterward?)
2. Is there a better way to group all of the metrics together, so we're not passing 9 variables from class to class in so many places?