- Look into `boost` as a way to bind C++ to Python

#### Ideas
1. Finish refactoring (Gymnasium onward)
2. Speed up video so that it isn't quite so slow for each frame
3. Quickly research a PLAYABLE AREA START event
4. Use a C++ implementation of PCA on all frames. Use `boost` to bootstrap that implementation to Python. Use an optional argument to recruit PCA or not, so we can write checkpoints of each. Perhaps the base path changes as `pca` and/or `raw`.
5. rcParams for final plot

#### Design
Metal Squirtle as logo

#### Extra
1. Build out a TSP implementation in C++ even if it isn't used