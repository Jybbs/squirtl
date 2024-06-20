from Experience import Experience

class Gymnasium:
    def __init__(self, agent, emulator, metrics, reward):
        self.agent    = agent
        self.emulator = emulator
        self.metrics  = metrics
        self.reward   = reward

    def run_episode(self):
        state = self.emulator.get_screen_image()
        done = False

        while not done:
            action_idx = self.agent.act(state)
            action = self.agent.settings.action_space[action_idx]
            self.emulator.press_button(action)

            next_state   = self.emulator.get_screen_image()
            reward, done = self.reward.calculate_reward(state, next_state)

            self.agent.cache(Experience(action_idx, done, next_state, reward, state))
            q_value, loss = self.agent.learn()

            self.metrics.log_step(reward, loss, q_value)

            state = next_state

        self.metrics.log_episode()

    def train(self, num_episodes):
        for episode in range(num_episodes):
            self.run_episode()
            self.metrics.record_episode(episode)
            self.agent.learn(episode)

        self.metrics.plot_metrics()
        self.emulator.close()