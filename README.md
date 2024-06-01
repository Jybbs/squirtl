# SquiRtL
*Exploring reinforcement learning and its core algorithms through Pokémon Blue*

**SquiRtL** aims to explore and implement various algorithms within a game environment, specifically focusing on Pokémon Blue pathfinding and optimal early gameplay. 

Inspired by **PWhiddy's Pokemon Red Experiments**, the project will involve researching and documenting algorithms intended to solve different categories of problems: Optimization, NP Complete, and a Wildcard algorithm. The motivation behind this project is to understand how one would leverage reinforcement learning strategies to enhance game-playing AI, providing both a practical application and a deep dive into the theoretical aspects of these algorithms.

## Algorithms

### Optimization Algorithm
*Game Visual State Compression using Principal Component Analysis (PCA)*

**Description:**
Apply PCA to compress and represent the visual game state obtained from the emulator's output. This optimization problem aims to reduce the dimensionality of the visual state representation while preserving the most important visual features, enabling more efficient processing and novelty detection.

**Steps:**
1. **Data Collection:** Collect a dataset of preprocessed visual state images by running the game and capturing the emulator's output at different points.
2. **PCA Implementation:** Implement the PCA algorithm to identify the principal components that capture the most variance in the visual state data.
3. **Visual State Compression:** Transform the original visual state images into a lower-dimensional space using the selected eigenvectors.
4. **Novelty Detection and Integration:** Use the compressed visual state representation to detect novel game states and integrate it into the AI agent's learning and decision-making pipeline, incorporating a novelty metric into the reward function.

**Research Reference:**
- **Chapter 29 (Linear Programming):** The sections on principal component analysis and dimensionality reduction provide the theoretical foundation for this optimization problem.

### NP Complete Algorithm
*Traveling Salesman Problem (TSP) for Optimal Route Planning*

**Description:**
The TSP can be applied to find the shortest possible route that visits a set of important locations (e.g., all gym leaders or item collection points) exactly once and returns to the starting point. This is crucial for optimizing in-game travel.

**Steps:**
1. **Problem Definition:** Define the key locations in the game that need to be visited (e.g., gyms, Pokecenters, key item locations).
2. **Graph Construction:** Create a complete graph where nodes represent these locations and edges represent the travel paths between them with associated distances or travel times.
3. **TSP Solution:** Implement a heuristic or approximation algorithm (e.g., nearest neighbor, Christofides' algorithm) to find a near-optimal solution to the TSP.
4. **Integration:** Use the TSP solution to guide the AI in planning its travel route efficiently within the game.

**Research Reference:**
- **Chapter 35 (Approximation Algorithms):** Techniques for solving NP-complete problems like the TSP using approximation algorithms.

### Wildcard Algorithm
*Reinforcement Learning with Deep Q-Network (DQN)*

**Description:**
Utilize a DQN algorithm to train an AI agent to play the game, focusing on exploration and reward optimization.

**Steps:**
1. **Environment Setup:** Use a Game Boy emulator to run the game and interact with it using a reinforcement learning framework.
2. **State Representation:** Represent the game state using visual inputs and encode necessary game state information (e.g., current location, health points).
3. **Reward Function:** Design a reward function that encourages exploration and game progression (e.g., reaching new areas, winning battles).
4. **DQN Implementation:** Implement the DQN algorithm to train the AI, leveraging libraries such as PyTorch.
5. **Training and Evaluation:** Train the AI on multiple parallel game instances and evaluate its performance.

**Research Reference:**
- **Chapter 33 (Machine-Learning Algorithms):** The sections on reinforcement learning and gradient descent provide the necessary background on learning algorithms and optimization techniques.
