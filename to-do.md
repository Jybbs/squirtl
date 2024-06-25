- Look into `boost` as a way to bind C++ to Python

#### Ideas
1. After optimization with PCA (of ndarrays passed via PyBoy), introduce a more encompassing penalty for backtracking (e.g. a backtrack is not just a copy of an exact state, but a copy of a PCA-optimized state)
2. rcParams for final plot
3. Tune hyperparameters to actually get checkpoints per run (instead of guessing numbers)
4. Save video clips per run
5. Is it possible that PyBoy returns some kind of information that says if a button press actually changed memory/data in some way, rather relying solely on the screen?