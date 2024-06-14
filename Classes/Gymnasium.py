from Experience import Experience

class Gymnasium:
    def __init__(self, agent, emulator, metrics, reward):
        self.agent    = agent
        self.emulator = emulator
        self.metrics  = metrics
        self.reward   = reward

    def calculate_reward(self, state, next_state):
        reward_value = self.reward.calculate_reward(state, next_state)
        return reward_value

    def close(self):
        self.emulator.close()

    def run(self, num_episodes):
        for episode in range(num_episodes):
            state = self.emulator.get_screen_image()
            done = False
            episode_reward = 0

            while not done:
                action_idx = self.agent.act(state)
                action = self.agent.settings.action_space[action_idx]
                self.emulator.press_button(action)

                next_state = self.emulator.get_screen_image()
                reward = self.calculate_reward(state, next_state)
                episode_reward += reward

                # Check if the EVENT_GOT_STARTER event has been triggered
                if self.reward.event_got_starter:
                    done = True

                self.agent.cache(Experience(action_idx, done, next_state, reward, state))
                q_value, loss = self.agent.learn()
                lr = self.agent.optimizer.param_groups[0]['lr']

                self.metrics.log_step(reward, loss, q_value, lr)

                state = next_state

            self.metrics.log_episode()
            self.metrics.record(episode, self.agent.hyperparameters['exploration_rate'], self.agent.current_step)

        self.close()