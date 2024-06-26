#### Ideas
1. Metrics: Backtracking is broken and Revisit is irrelevant. Count and plot the number of "Waits" instead.
1. Use a C++ implementation of PCA on all frames. Use `boost` to bootstrap that implementation to Python. Use an optional argument to recruit PCA or not, so we can write checkpoints of each. Perhaps the base path changes as `pca` and/or `raw`.
2. rcParams for final plot

#### Design
Metal Squirtle as logo

#### Extra
1. Build out a TSP implementation in C++ even if it isn't used