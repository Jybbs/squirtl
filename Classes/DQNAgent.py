import numpy as np

class DQNAgent:
    def __init__(self, action_space):
        self.action_space = action_space
        self.memory       = []    # Store transitions for learning
        self.gamma        = 0.99  # Discount factor for future rewards

    def select_action(self):
        return np.random.choice(self.action_space) # Random action for now; replace with policy network inference later

    def store_transition(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))
