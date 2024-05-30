from Emulator import Emulator
from PPOAgent import PPOAgent
import numpy as np

class Gymnasium:
    def __init__(self, rom_path, action_space):
        self.emulator          = Emulator(rom_path)
        self.ppo_agent         = PPOAgent(action_space)
        self.prev_screen       = self.get_screen_array()
        self.cumulative_reward = 0

    def calculate_reward(self, state, next_state):
        if not np.array_equal(state, next_state):
            return 1
        return 0

    def close(self):
        self.emulator.close()

    def get_screen_array(self):
        return self.emulator.pyboy.screen.ndarray
    
    def run(self):
        try:
            while True:
                state  = self.get_screen_array()
                action = self.ppo_agent.select_action()  # PPO agent selects action
                self.emulator.press_button(action)

                next_state = self.get_screen_array()
                reward     = self.calculate_reward(state, next_state)
                self.cumulative_reward += reward
                done = False  # Update this based on your game logic

                self.ppo_agent.store_transition(state, action, reward, next_state, done)

                if done:
                    self.ppo_agent.update_policy()
                    break

        except KeyboardInterrupt:
            self.close()