# SquiRtL
*Exploring reinforcement learning and its core algorithms through Pokémon Blue*

SquiRtL is a project that explores the application of reinforcement learning techniques to play Pokémon Blue. The project aims to create an AI agent capable of learning and optimizing gameplay strategies through interaction with the game environment. 

With the support of deep Q-learning networks (DQN), SquiRtL demonstrates how machine learning can be applied to complex game environments, offering insights into AI decision-making processes and optimization techniques.

## Installation

To set up the SquiRtL project, follow these steps:

1. Ensure you have Python 3.12 or later installed on your system.

2. Install [Poetry](https://python-poetry.org), a dependency management tool for Python, if you haven't already.

3. Clone this repository.

4. Install dependencies using Poetry via `poetry install`.

5. **Important**: You must supply your own legal copy of either Pokémon Red or Blue ROM file. Place the ROM file in the project root directory and name it `PokemonBlue.gb` or update the `rom_path` in the configuration accordingly.

This will set up a virtual environment with all necessary dependencies as specified in the `pyproject.toml` file.

### Key Packages

- **PyTorch**: The core deep learning framework used for implementing the Deep Q-Network.
  - Used in: `Agent.py`, `DQN.py`
  - Purpose: Neural network definition, training, and inference.

- **NumPy**: Provides efficient array operations and numerical computing tools.
  - Used in: Most files, particularly `Frames.py`
  - Purpose: Efficient state representation and manipulation.

- **PyBoy**: A Game Boy emulator written in Python.
  - Used in: `Emulator.py`
  - Purpose: Provides the game environment for the agent to interact with.

- **Matplotlib** and **Seaborn**: Data visualization libraries.
  - Used in: `Logging.py`
  - Purpose: Generate performance plots and visualize training progress.

- **OpenCV (cv2)**: Computer vision library.
  - Used in: `Logging.py`
  - Purpose: Video generation of gameplay episodes.

## Reinforcement Learning Overview

Reinforcement Learning (**RL**) is a paradigm of machine learning where an agent learns to make decisions by interacting with an environment. In the context of Pokémon Blue, RL is particularly interesting due to the game's complex state space, delayed rewards, and sequential decision-making nature.

### Key RL Concepts in SquiRtL

1. **State Space**: Represented by the game screen pixels (*144x160x4 tensor*). This representation is crucial as it allows the agent to learn directly from raw pixel data, mimicking human visual input. It presents a challenge in processing high-dimensional input and extracting relevant features for decision-making.

2. **Action Space**: Discrete set of possible game controls (*'a', 'b', 'up', 'down', 'left', 'right', 'wait'*). This limited, discrete action space reflects the actual game controls available to a human player. It simplifies the decision-making process compared to continuous action spaces, but still requires the agent to learn complex sequences of actions to achieve goals with nuance, like waiting for the opportune time to take an action.

3. **Reward Function**: Designed to encourage exploration, progress, and optimal gameplay. The reward function is critical as it shapes the agent's behavior. In this project, it's particularly interesting because it needs to guide the agent through the complex, multi-step process of starting the game and choosing a starter Pokémon, without direct instruction.

4. **Policy**: The strategy the agent uses to determine the next action based on the current state. The policy is the core of the agent's decision-making process. In this project, it must learn to navigate the game world, interact with NPCs, and make progress towards objectives, all from pixel inputs.

5. **Value Function**: Estimates the expected cumulative reward from a given state. In Pokémon Blue, many actions don't have immediate rewards, so the agent must learn to value states that lead to future rewards, like progressing through dialogue or moving towards important locations.

6. **Experience Replay**: A technique where the agent stores and learns from past experiences. This is particularly important in this project due to the rarity of significant events (*like completing the intro or choosing a starter*). Experience replay allows the agent to learn efficiently from these rare but important experiences.

### Deep Q-Networks (DQN)

SquiRtL utilizes Deep Q-Networks (**DQN**), a groundbreaking reinforcement learning algorithm that combines Q-learning with deep neural networks. Introduced by **DeepMind** in 2013, DQN represented a significant leap forward in RL's ability to handle complex, high-dimensional state spaces.

Q-learning, a foundational RL technique, had long been effective for small, discrete state spaces, but it struggled with the curse of dimensionality in larger environments. The key innovation of DQN was to approximate the Q-function using a deep neural network, allowing it to generalize across vast state spaces. This combination is particularly powerful for tasks with visual inputs, like Atari games or, in our case, Pokémon Blue. The convolutional layers in the neural network can automatically learn to extract relevant features from raw pixel data, mimicking the human visual system's ability to understand game states from screen images.

Beyond game playing, DQN and its variants have found applications in:

1. **Robotics**: For learning complex manipulation tasks from visual input.

2. **Recommendation systems**: To handle large user-item interaction spaces.

3. **Resource management**: In complex systems like datacenter cooling.

4. **Trading**: For developing purchasing strategies in financial markets.

The success of DQN in these diverse domains stems from its ability to learn effective representations of complex state spaces, making it an ideal choice for the multifaceted environment of Pokémon Blue.

### In Mathematical Terms

The Q-function, $Q(s, a)$, represents the expected cumulative reward of taking action $a$ in state $s$ and then following the optimal policy thereafter. This function embodies the principle of **optimal substructure**, an important concept in dynamic programming approaches, as the optimal solution can be constructed from optimal solutions of subproblems.

The **Bellman equation**, fundamental to many areas of dynamic programming, forms the basis of the Q-learning update:

$\hspace{0.5cm} \displaystyle Q(s, a) = \mathbb{E}[R(s, a) + \gamma \text{max}_{a'} Q(s', a')]$  

Where:

- $R$ is the immediate reward

- $\gamma \in [0, 1]$ is the discount factor, analogous to the role of weights in weighted graph algorithms

- $s'$ is the next state

- $a'$ is the action in the next state

This equation represents a contraction mapping in the space of value functions, guaranteeing convergence to a unique fixed point (*the optimal Q-function*) under certain conditions. Interestingly enough, this is reminiscent of the convergence properties of other iterative algorithms in Bellman's purview, like the Bellman-Ford algorithm for finding shortest paths.

In practice, we use a neural network $Q(s, a; \theta)$ to approximate $Q(s, a)$. This approximation transforms the problem from a tabular method to a function approximation method, allowing us to handle the curse of dimensionality in large state spaces. The network is trained to minimize the loss:

$\hspace{0.5cm} \displaystyle L(\theta) = \mathbb{E}_{(s, a, r, s') \sim U(D)} - \left((Q(s, a; \theta))^2\right)$

Where:

- $y = r + \gamma \text{max}_{a'} Q(s', a'; \theta^-)$ is the target Q-value

- $\theta$ are the parameters of the online network

- $\theta^-$ are the parameters of the target network

- $U(D)$ is a uniform distribution over the replay buffer D

This loss function is a form of temporal difference learning, where we bootstrap our current estimates to form the targets. The use of a separate target network $\theta^-$ is analogous to the concept of "relaxation" in approximation algorithms, where we temporarily fix part of the solution to make the optimization problem more tractable.

The gradient of the loss with respect to the network parameters is:

$\hspace{0.5cm} \displaystyle \nabla_{\theta} L(\theta) = \mathbb{E}_{(s, a, r, s') \sim U(D)} \left((r + \gamma \text{max}_{a'} Q(s', a'; \theta^{-}) - Q(s, a; \theta)) \nabla_{\theta} Q(s, a; \theta)\right)$

This gradient form allows for stochastic gradient descent, connecting our DQN implementation to the broader family of iterative improvement algorithms.

In SquiRtL, we use an epsilon-greedy policy for action selection:

$\hspace{0.5cm} \displaystyle \pi(a|s) = \begin{cases} 
\epsilon / |A| + (1-\epsilon), & \text{if } a = \argmax_{a'} Q(s, a'; \theta) \\
\epsilon / |A|, & \text{otherwise}
\end{cases}$

Where $|A|$ is the size of the action space.

The exploration rate $\epsilon$ decays over time:

$\hspace{0.5cm} \displaystyle \epsilon_{t} = \text{max}(\epsilon_{\text{min}}, \epsilon_0 \cdot \epsilon_{\text{decay}}^t)$

This decay schedule is most analogous to the cooling schedule in simulated annealing, gradually shifting from exploration to exploitation as the agent gains more knowledge about the environment.

Within this framework, the DQN algorithm employs a separate target network $Q(s, a; \theta^-)$ which is periodically updated:

$\hspace{0.5cm} \displaystyle \theta^- \leftarrow \theta \text{ every } N \text{ steps}$

This periodic update is reminiscent of the concept of "batching" in amortized analysis, where we perform expensive operations (*updating the target network*) less frequently to reduce overall computational cost while maintaining performance guarantees.

### Application to Pokémon Blue

In the context of Pokémon Blue, the state $s$ is represented by a tensor of shape (144, 160, 4), corresponding to the game screen pixels. The action space $A$ consists of 7 discrete actions: 'a', 'b', 'up', 'down', 'left', 'right', and 'wait'.

The reward function $R(s, a, s')$ is designed to encourage exploration and progress:

$\hspace{0.5cm} R(s, a, s') = \begin{cases}
10, & \text{if } s' \text{ is a new state} \\
-10, & \text{if } s' \text{ is a recent backtrack} \\
-1, & \text{if } a \text{ is ineffective} \\
0.1, & \text{if } s' \text{ is a revisited state} \\
1000, & \text{if intro is completed} \\
10000, & \text{if starter is chosen}
\end{cases}$

This reward structure, combined with the DQN algorithm, allows SquiRtL to learn a policy that can navigate the complex, partially observable environment of Pokémon Blue, dealing with delayed rewards and a large state space.

## Class Structure and Components

SquiRtL is composed of several interconnected classes:

1. **Orchestrator**: The main class that initializes and coordinates all components.
    - Initializes all other components
    - Manages the training process

2. **Agent**: Implements the DQN algorithm, including action selection and learning.
    - Selects actions using an epsilon-greedy strategy
    - Stores experiences in replay memory
    - Performs learning updates on the DQN

3. **DQN**: Defines the neural network architecture for Q-value prediction.
    - Implements the deep neural network structure
    - Performs forward passes to predict Q-values

4. **Emulator**: Interfaces with the Pokémon Blue game using PyBoy.
    - Manages the game state
    - Executes actions in the game environment
    - Provides observations (screen states)

5. **Frames**: Manages game frames, including state representation and novelty detection.
    - Processes and stores game frames
    - Detects new game states
    - Checks for backtracking

6. **Gymnasium**: Coordinates the interaction between the agent and the environment.
    - Manages episodes
    - Handles action execution and reward calculation
    - Facilitates the agent-environment loop

7. **Logging**: Handles metrics logging and visualization.
    - Collects performance metrics
    - Generates visualizations and progress reports

8. **Reward**: Defines the reward structure for the agent.
    - Calculates rewards based on game events and agent actions
    - Implements the reward shaping strategy

9. **Settings**: Centralizes all configuration parameters.
    - Stores hyperparameters and game settings
    - Provides a single point of configuration for the entire system

These components work together to create a complete reinforcement learning system. The **Orchestrator** initializes the process, the **Agent** interacts with the **Gymnasium**, which uses the **Emulator** to execute actions and observe states. The **Frames** class assists in state processing, while the **Reward** class provides feedback. The **DQN** is used by the **Agent** for action selection and learning as it borrows hyperparameters from **Settings**, and the **Logging** class tracks the overall performance.

## Metrics and Analysis

![Training Metrics Over 10 Episodes](https://i.ibb.co/hR0hrYk/plot-episode-10.png)
*Figure 1: Performance metrics for the first 10 training episodes of the SquiRtL agent*

To gain initial insights into our reinforcement learning agent's behavior, we conducted a preliminary experiment consisting of 10 training episodes. These episodes were run using the default parameter set as defined in the repository, without any adjustments between runs. It's important to note that this represents only a brief interaction with the environment—approximately an hour of simulated gameplay—whereas reinforcement learning frameworks typically achieve optimal performance after much longer training periods, often equivalent to years of gameplay.

Therefore, the following analysis should be interpreted as an early snapshot of the agent's learning process, rather than a representation of its full potential. These initial results provide valuable insights into the agent's early learning trends and potential areas for improvement in the algorithm or reward structure.

Based on the provided chart for these first 10 training episodes, we can observe several interesting trends:

1. **Total Actions**: Remains relatively constant across episodes, indicating consistent episode lengths.

2. **Total Reward**: Shows high variability, with a peak around episode 4-5, followed by a decline. This suggests the agent initially improves but then struggles to maintain performance, possibly due to exploration vs. exploitation trade-offs.

3. **Average Loss**: Steadily increases over time, which is somewhat concerning. This could indicate that the agent is finding it increasingly difficult to predict Q-values accurately, possibly due to encountering more complex game states.

4. **Average Q Value**: Shows a clear upward trend, suggesting that the agent is learning to assign higher values to states and actions over time. This is generally a positive sign, indicating that the agent believes it's finding more rewarding strategies.

5. **Effective Actions**: Increases initially but plateaus around episode 6-7. This suggests the agent is learning to take more meaningful actions but may be reaching a local optimum.

6. **New Actions**: Peaks around episode 7 and then declines. This pattern is typical in exploration phases, where the agent initially discovers many new states but then starts to revisit known areas more frequently.

7. **Backtracking Actions**: Shows an overall increasing trend, which might indicate the agent is learning to revisit beneficial states or is struggling to find new productive paths.

8. **Wait Actions**: Decreases initially but rises sharply in later episodes. This could be a sign that the agent is becoming more indecisive or is stuck in certain game states.

9. **Elapsed Time**: Increases initially and then stabilizes, which is expected as the agent learns to interact with the game more effectively.

These trends suggest that while the agent is showing signs of learning (*increasing Q-values, more effective actions initially*), it's also facing challenges in consistently improving its performance. The rising loss and increased wait actions in later episodes indicate that there might be room for improvement in the learning algorithm or reward structure.

## Computational Complexity Analysis

Taking a moment to contextualize the SquiRtL implementation through the lens of asymptotic analysis, we'll examine both time and space complexity, providing insights into the scalability and efficiency of our reinforcement learning system.

### Time Complexity

1. **Neural Network Forward Pass**: $\mathcal{O}(L n^2)$, where $L$ is the number of layers and $n$ is the maximum number of neurons in any layer.

   For a fully connected layer, the complexity is $\mathcal{O}(n_in_o)$, where $n_i$ and $n_o$ are the number of input and output neurons respectively. For convolutional layers, it's $\mathcal{O}(d^2 k n_i n_o)$, where $d$ is the filter size and $k$ is the number of filters.

   Summing over $L$ layers, we get $\mathcal{O}(L n^2)$ in the worst case, where $n$ is the maximum of $n_i$ and $n_o$ across all layers.

2. **Experience Replay Sampling**: $\mathcal{O}(b)$, where $b$ is the batch size.

   We employ reservoir sampling to achieve uniform sampling in constant time per sample. The algorithm maintains a reservoir of size $b$ and processes the stream of experiences in a single pass. For each experience, it is selected for the reservoir with probability $b/i$, where $i$ is the index of the current experience.

   The expected number of reservoir updates is:

   $\hspace{0.5cm} \displaystyle \sum_{i=b+1}^n \frac{b}{i} \approx b \ln(\frac{n}{b})$

   where $n$ is the total number of experiences. However, as we only need ever $b$ samples, the time complexity remains $\mathcal{O}(b)$.

3. **Q-Value Update**: $\mathcal{O}(b L n^2)$ for a batch of experiences.

   This operation involves updating the Q-values for a batch of b experiences. For each experience in the batch, we perform two main steps:

   **Forward Pass**: $\mathcal{O}(L n^2)$
      - For each of the L layers, we perform matrix multiplication between the input (size n) and the weights (size n x n in the worst case).
      - This results in $\mathcal{O}(n^2)$ operations per layer.
      - Across L layers, this sums to $\mathcal{O}(L n^2)$.

   **Backpropagation**: $\mathcal{O}(L n^2)$
      - We compute gradients starting from the output layer back to the input.
      - For each layer, we perform matrix multiplications similar to the forward pass.
      - This again results in $\mathcal{O}(L n^2)$ operations.

   The forward pass and backpropagation are performed for each of the $b$ samples in the batch. Therefore, the total complexity is:

   $\hspace{0.5cm} \displaystyle \mathcal{O}(b) * (\mathcal{O}(L n^2) + \mathcal{O}(L n^2)) = \mathcal{O}(b L n^2)$

   It's worth noting that this is a worst-case analysis assuming fully connected layers. In practice, convolutional layers and optimization techniques can affect the actual runtime, but this represents the upper bound of the complexity.

4. **Frame Processing**: $\mathcal{O}(wh)$, where $w$ and $h$ are the width and height of the game screen.

   This complexity arises from the need to process each pixel of the input frame. Operations like convolution or simple transformations typically require touching each pixel at least once, leading to this linear complexity in the number of pixels. Therefore, this is constant for each state.

5. **State Novelty Check**: $\mathcal{O}(m wh)$ in the worst case, where $m$ is the number of explored states.

   We need to compare the current state (*of size $wh$*) with all $m$ previously seen states. Each comparison takes $\mathcal{O}(wh)$ time, leading to a total complexity of essentially $\mathcal{O}(m)$, since $wh$ is a constant.

6. **Action Selection**: $\mathcal{O}(L n^2 + |A|)$, where $|A|$ is the size of the action space.

   This involves a forward pass through the network ($\mathcal{O}(L n^2)$) followed by selecting the maximum Q-value ($\mathcal{O}(|A|)$).

The overall time complexity per step, expressed in terms of the dominant term, therefore, is $\mathcal{O}(b L n^2)$. This is because the batch processing of the neural network operations (**Q-Value Update**) typically dominates the computation time, especially as the network grows in size and complexity.

### Space Complexity

- **Experience Replay Buffer**: $\mathcal{O}(k wh)$, where k is the buffer capacity.
  This fixed-size buffer stores experiences as (state, action, reward, next_state) tuples, where each state is of size wh.

- **Neural Network Parameters**: $\mathcal{O}(L n^2)$
  This accounts for storing all weights and biases of the network across L layers.

- **Explored States**: $\mathcal{O}(m wh)$
  We maintain a record of all unique states encountered, each of size wh, growing with exploration.

The total space complexity, likewise to **Time Complexity**, is $$\mathcal{O}(L n^2)$. This is because the storage of explored states typically becomes the dominant factor as the agent explores more of the game environment, especially for high-resolution game screens.

### Trade-offs and Optimizations

1. **Experience Replay**: This introduces a trade-off between space complexity and sample efficiency. While it increases space requirements by a non-dominant term of $\mathcal{O}(k wh)$, it significantly improves sample efficiency by allowing reuse of experiences.

2. **State Representation**: The current pixel-based state representation (*$wh$ pixels*) is memory-intensive. Dimensionality reduction techniques could potentially reduce this, trading off some information for improved space efficiency.

3. **Novelty Detection**: As $m$ grows, the $\mathcal{O}(m wh)$ novelty check becomes a significant bottleneck. Potential optimizations include:

   - Using tree-based structures could reduce this to $\mathcal{O}(\log m)$ on average, at the cost of increased complexity in insertions.
- 
   - Locality-sensitive hashing (**LSH**) could provide approximate nearest neighbor search in sublinear time.
- 
   - Bloom filters could offer constant-time novelty checking with a small false positive rate.

1. **Batch Processing**: The batch size $b$ presents a trade-off between computation time and learning stability. Larger batches provide more stable gradient estimates but increase per-step computation time.

2. **Network Architecture**: The number of layers $L$ and neurons $n$ significantly impacts both time and space complexity. Techniques like pruning or quantization could reduce these at the cost of potential reduction in model capacity.

3. **GPU Acceleration**: While not changing asymptotic complexity, GPU usage can significantly reduce practical computation time for neural network operations, as was often the case in my initial training.

In conclusion, SquiRtL's complexity is primarily driven by the neural network operations, the size of the game state, and the number of explored states. As the agent explores more of the game, optimizations in state representation and novelty detection will become crucial for maintaining efficiency in long training runs.

## References

1. Cormen, T. H., Leiserson, C. E., Rivest, R. L., & Stein, C. (2022). *Introduction to Algorithms*, 4th edition. MIT Press.
2. David, O., Netanyahu, N., & Wolf, L. (2016). [DeepChess: End-to-End Deep Neural Network for Automatic Learning in Chess](http://arxiv.org/pdf/1711.09667).
3. GeeksforGeeks. (2016, Oct 26). *Dynamic Programming | Algorithms & Data Structures* [Playlist of Videos]. YouTube. Available at: [https://www.youtube.com/playlist?list=PLqM7alHXFySGbXhWx7sBJEwY2DnhDjmxm](https://www.youtube.com/playlist?list=PLqM7alHXFySGbXhWx7sBJEwY2DnhDjmxm).
4. Kreutzer, S. (2006). [DAG-Width and Parity Games](http://web.comlab.ox.ac.uk/people/Stephan.Kreutzer/Publications/stacs06.pdf).
5. Mnih, V., Kavukcuoglu, K., Silver, D., Graves, A., Antonoglou, I., Wierstra, D., & Riedmiller, M. (2013). [Playing Atari with Deep Reinforcement Learning](https://arxiv.org/abs/1312.5602). arXiv preprint arXiv:1312.5602.
6. OpenAI. (2018). [OpenAI Baselines: high-quality implementations of reinforcement learning algorithms](https://github.com/openai/baselines). GitHub repository. Available at: [https://github.com/openai/baselines](https://github.com/openai/baselines).
7. PWhiddy. *Pokemon Red Experiments*. GitHub repository. Available at: [https://github.com/PWhiddy/PokemonRedExperiments](https://github.com/PWhiddy/PokemonRedExperiments).
8. PyBoy. GitHub repository. Available at: [https://github.com/Baekalfen/PyBoy](https://github.com/Baekalfen/PyBoy).
9. Sutton, R. S., & Barto, A. G. (2018). *Reinforcement Learning: An Introduction*, 2nd edition. MIT Press.
10. Viles, W. D. (2024, Jun 26). *CS5800: Algorithms Course Notes*. Northeastern University.
11. Viles, W. D. (2024, Jun 26). *CS5800: Algorithms Homework Solutions*. Northeastern University.