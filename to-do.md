- Look into `boost` as a way to bind C++ to Python

#### Ideas
1. Implement a "wait" action that doesn't result in a button press, a reward calculation, or an action logged for metric tracking. It's simply an Experience (or a choice) for the Agent to learn from during certain screens.
2. Don't consider an empty screen "playable" ever
3. After optimization with PCA (of ndarrays passed via PyBoy), introduce a more encompassing penalty for backtracking (e.g. a backtrack is not just a copy of an exact state, but a copy of a PCA-optimized state)
4. rcParams for final plot
5. Add an argument that starts the Agent at a given numeric checkpoint, if it exists

#### Design
Metal Squirtle as logo