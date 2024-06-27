#### Ideas
1. Use a C++ implementation of PCA on all frames. Use `boost` to bootstrap that implementation to Python. Use an optional argument to recruit PCA or not, so we can write checkpoints of each. Perhaps the base path changes as `pca` and/or `raw`. Use comments throughout.
2. Teach Gymnasium to pick up and log everything after the `start_episode`. It trained on the checkpoint properly, but it then plotted and logged metrics as if this were episode 1 and not start_episode = X


#### Design
Metal Squirtle as logo