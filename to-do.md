- Look into `boost` as a way to bind C++ to Python

#### Ideas
1. Use a C++ implementation of PCA on all frames. Use `boost` to bootstrap that implementation to Python. Use an optional argument to recruit PCA or not, so we can write checkpoints of each. Perhaps the base path changes as `pca` and/or `raw`.
2. rcParams for final plot
3. Add an argument that starts the Agent at a given numeric checkpoint, if it exists.
4. Do we need a stalling penalty?

#### Design
Metal Squirtle as logo

#### Extra
1. Build out a TSP implementation in C++ even if it isn't used