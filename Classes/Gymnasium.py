from Experience import Experience

class Gymnasium:
    def __init__(self, settings, agent, emulator, metrics, reward):
        self.agent    = agent
        self.emulator = emulator
        self.metrics  = metrics
        self.reward   = reward
        self.settings = settings

    def run_episode(self):
        self.reward.reset() # Reset the visited states at the start of each episode
        current_state   = self.emulator.reset_emulator()
        episode_done    = False
        episode_length  = 0
        episode_loss    = 0
        episode_q_value = 0
        total_reward    = 0

        while not episode_done:
            action_index = self.agent.select_action(current_state)
            action       = self.settings.action_space[action_index]
            
            self.emulator.press_button(action)
            next_state = self.emulator.get_screen_image()
            reward, episode_done = self.reward.evaluate_action(current_state, next_state)

            experience = Experience(current_state, action_index, next_state, reward, episode_done)
            self.agent.store_experience(experience)
            step_loss, step_q_value = self.agent.learn_from_experience()

            current_state    = next_state
            total_reward    += reward
            episode_length  += 1
            episode_loss    += step_loss
            episode_q_value += step_q_value

        average_loss    = episode_loss    / episode_length if episode_length > 0 else 0
        average_q_value = episode_q_value / episode_length if episode_length > 0 else 0

        return episode_length, total_reward, average_loss, average_q_value

    def train(self, num_episodes):
        for episode in range(num_episodes):
            length, reward, loss, q_value = self.run_episode()
            self.metrics.log_episode(length, reward, loss, q_value)

            if (episode + 1) % self.settings.save_interval == 0:
                self.agent.save_checkpoint(f"checkpoint_episode_{episode+1}.pth")

        self.metrics.close_writer()
        self.emulator.close_emulator()