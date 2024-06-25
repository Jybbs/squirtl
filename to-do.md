- Look into `boost` as a way to bind C++ to Python

#### Ideas
1. Implement a "wait" action that doesn't result in a button press, a reward calculation, or an action logged for metric tracking. It's simply an Experience (or a choice) for the Agent to learn from during certain screens.
2. Don't consider an empty screen "playable" ever
3. Use a C++ implementation of PCA on all frames. Use `boost` to bootstrap that implementation to Python. Use an optional argument to recruit PCA or not, so we can write checkpoints of each. Perhaps the base path changes as `pca` and/or `raw`.
4. rcParams for final plot
5. Add an argument that starts the Agent at a given numeric checkpoint, if it exists.

#### Design
Metal Squirtle as logo

#### Extra
1. Build out a TSP implementation in C++ even if it isn't used