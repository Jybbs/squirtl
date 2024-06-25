from dataclasses import dataclass
from Logging     import Metrics
from numpy       import array
from torch       import BoolTensor, FloatTensor, LongTensor
from time        import time

@dataclass
class Experience:
    state      : list
    action     : int
    next_state : list
    reward     : float
    done       : bool

    def __iter__(self):
        return iter((self.state, self.action, self.next_state, self.reward, self.done))

    @staticmethod
    def batch_to_tensor(experiences, device):
        batch = zip(*experiences)
        return Experience \
        (
            state      = FloatTensor(array(next(batch))).to(device),
            action     = LongTensor(array(next(batch))).to(device),
            next_state = FloatTensor(array(next(batch))).to(device),
            reward     = FloatTensor(array(next(batch))).to(device),
            done       = BoolTensor(array(next(batch))).to(device)
        )
    
class Gymnasium:
    def __init__(self, settings, agent, emulator, logging, reward):
        self.agent    = agent
        self.emulator = emulator
        self.logging  = logging
        self.reward   = reward
        self.settings = settings

    def determine_action_type(self, action_effective, next_state_hash, current_state_hash):
        if not action_effective:
            return "ineffective"
        if self.reward.is_unexplored_state(next_state_hash):
            return "unexplored"
        if self.reward.is_backtracking(current_state_hash):
            return "backtracking"
        return "revisit"

    def run_episode(self):
        self.reward.reset()
        action_number = 0
        current_state = self.emulator.reset_emulator()
        episode_done  = False
        start_time    = time()
        total_reward  = 0

        while not episode_done and action_number < self.settings.MAX_ACTIONS:
            action_index = self.agent.select_action(current_state)
            action       = self.settings.action_space[action_index]
            
            is_effective, next_state = self.emulator.press_button(action)
            action_reward, episode_done = self.reward.evaluate_action(current_state, next_state, is_effective)
            
            total_reward += action_reward
            action_type   = self.determine_action_type(is_effective, next_state, current_state)
            experience    = Experience(current_state, action_index, next_state, action_reward, episode_done)

            self.agent.store_experience(experience)
            action_loss, action_q_value = self.agent.learn_from_experience()

            self.logging.log_action(self.current_episode, Metrics \
            (
                action        = action,
                action_index  = action_index,
                action_number = action_number,
                action_type   = action_type,
                elapsed_time  = time() - start_time,
                is_effective  = is_effective,
                loss          = action_loss,
                q_value       = action_q_value,
                reward        = action_reward,
                total_reward  = total_reward
            ))

            current_state  = next_state
            action_number += 1

        self.logging.print_episode_summary(self.current_episode)
        return self.logging.calculate_episode_metrics(self.current_episode)

    def train(self, num_episodes):
        for self.current_episode in range(num_episodes):
            self.run_episode()

            if (self.current_episode + 1) % self.settings.save_interval == 0:
                self.agent.save_checkpoint(self.settings.checkpoints_directory / f"checkpoint_episode_{self.current_episode+1}.pth")

        self.logging.plot_metrics()
        self.logging.save_metrics()
        self.emulator.close_emulator()