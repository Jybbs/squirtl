import numpy as np

class PPOAgent:
    def __init__(self, action_space):
        self.action_space = action_space

    def select_action(self):
        # Select a random action from the action space
        return np.random.choice(self.action_space)
