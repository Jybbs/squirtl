from Experience import Experience
from Logging    import Metrics
from time       import time

class Gymnasium:
    def __init__(self, settings, agent, emulator, logging, reward):
        self.agent      = agent
        self.emulator   = emulator
        self.logging    = logging
        self.reward     = reward
        self.settings   = settings

    def run_episode(self):
        self.reward.reset()
        start_time         = time()
        current_state_hash = self.emulator.reset_emulator()
        episode_done       = False
        episode_length     = 0
        episode_loss       = 0
        episode_q_value    = 0
        total_reward       = 0

        effective_actions    = 0
        ineffective_actions  = 0
        unexplored_actions   = 0
        backtracking_actions = 0
        revisit_actions      = 0

        while not episode_done:
            action_index = self.agent.select_action(current_state_hash)
            action       = self.settings.action_space[action_index]
            
            is_effective, next_state_hash = self.emulator.press_button(action)
            
            reward, episode_done = self.reward.evaluate_action(current_state_hash, next_state_hash, is_effective)

            # Update action counters
            if is_effective:
                effective_actions += 1
                if self.reward.is_unexplored_state(next_state_hash):
                    unexplored_actions += 1
                elif self.reward.is_backtracking(current_state_hash):
                    backtracking_actions += 1
                else:
                    revisit_actions += 1
            else:
                ineffective_actions += 1

            experience = Experience(current_state_hash, action_index, next_state_hash, reward, episode_done)
            self.agent.store_experience(experience)
            action_loss, action_q_value = self.agent.learn_from_experience()

            current_state_hash = next_state_hash
            total_reward      += reward
            episode_length    += 1
            episode_loss      += action_loss
            episode_q_value   += action_q_value

            if episode_length >= self.settings.MAX_ACTIONS:
                episode_done = True

        average_loss    = episode_loss    / episode_length if episode_length > 0 else 0
        average_q_value = episode_q_value / episode_length if episode_length > 0 else 0

        return Metrics \
        (
            backtracking_actions = backtracking_actions,
            effective_actions    = effective_actions,
            elapsed_time         = time() - start_time,
            episode              = self.current_episode,
            ineffective_actions  = ineffective_actions,
            length               = episode_length,
            loss                 = average_loss,
            q_value              = average_q_value,
            revisit_actions      = revisit_actions,
            reward               = total_reward,
            unexplored_actions   = unexplored_actions
        )

    def train(self, num_episodes):
        for self.current_episode in range(num_episodes):
            metrics = self.run_episode()
            self.logging.log_episode(metrics)

            if (self.current_episode + 1) % self.settings.save_interval == 0:
                self.agent.save_checkpoint(self.settings.checkpoints_directory / f"checkpoint_episode_{self.current_episode+1}.pth")

        self.logging.plot_metrics()
        self.emulator.close_emulator()