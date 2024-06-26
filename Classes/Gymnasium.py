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
    def __init__(self, agent, debug, emulator, logging, reward, settings):
        self.agent    = agent
        self.debug    = debug
        self.emulator = emulator
        self.logging  = logging
        self.reward   = reward
        self.settings = settings

    def run_episode(self):
        self.reward.reset()
        action_number = 0
        current_frame = self.emulator.reset()
        episode_done  = False
        start_time    = time()
        total_reward  = 0

        while not episode_done and action_number < self.settings.MAX_ACTIONS:
            current_frame = self.emulator.advance_until_playable()
            
            action_index = self.agent.select_action(current_frame)
            action = self.settings.action_space[action_index]

            if action == 'wait':
                next_frame    = self.emulator.wait()
                experience    = Experience(current_frame, action_index, next_frame, 0, False)
                self.agent.store_experience(experience)
                current_frame = next_frame

                if self.debug:
                    print("Waiting 1 tick.")
                continue
            
            is_effective, next_frame = self.emulator.press_button(action)
            action_reward, episode_done, action_type = self.reward.evaluate_action(current_frame, next_frame, is_effective)
            
            total_reward += action_reward

            experience = Experience(current_frame, action_index, next_frame, action_reward, episode_done)
            self.agent.store_experience(experience)
            action_loss, action_q_value = self.agent.learn_from_experience()

            self.logging.log_action(self.current_episode, Metrics \
            (
                action        = action,
                action_number = action_number,
                action_type   = action_type,
                elapsed_time  = time() - start_time,
                is_effective  = is_effective,
                loss          = action_loss,
                q_value       = action_q_value,
                reward        = action_reward,
                total_reward  = total_reward
            ))

            current_frame = next_frame
            action_number += 1

        self.logging.save_episode_video(self.current_episode)
        self.logging.print_episode_summary(self.current_episode)
        return self.logging.calculate_episode_metrics(self.current_episode)

    def train(self, num_episodes):
        for self.current_episode in range(num_episodes):
            self.run_episode()
            
            # Save checkpoint at the end of each episode
            self.agent.save_checkpoint(self.settings.checkpoints_directory / f"checkpoint_episode_{self.current_episode + 1}.pth")

        self.logging.plot_metrics()
        self.logging.save_metrics()
        self.emulator.close_emulator()