from Emulator import Emulator
from Agent import Agent
from MetricLogger import MetricLogger
import numpy as np

class Gymnasium:
    def __init__(self, rom_path, action_space, state_dim, save_dir, date, hyperparameters):
        self.cumulative_reward = 0
        self.emulator = Emulator(rom_path)
        self.metric_logger = MetricLogger(save_dir)
        self.agent = Agent(state_dim, action_space, save_dir, date, hyperparameters)

    def calculate_reward(self, state, next_state):
        # Implement reward calculation logic here
        reward = 0
        return reward

    def close(self):
        self.emulator.close()

    def run(self, num_episodes):
        for episode in range(num_episodes):
            state = self.emulator.get_screen_image()
            done = False
            episode_reward = 0

            while not done:
                action_idx = self.agent.act(state)
                action = self.agent.action_space[action_idx]
                self.emulator.press_button(action)

                next_state = self.emulator.get_screen_image()
                reward = self.calculate_reward(state, next_state)
                episode_reward += reward
                done = False  # Update this based on your game logic

                self.agent.cache(state, next_state, action_idx, reward, done)
                q_value, loss = self.agent.learn()
                lr = self.agent.optimizer.param_groups[0]['lr']

                self.metric_logger.log_step(reward, loss, q_value, lr)

                state = next_state

            self.metric_logger.log_episode()
            self.metric_logger.record(episode, self.agent.hyperparameters.exploration_rate, self.agent.curr_step)

        self.close()