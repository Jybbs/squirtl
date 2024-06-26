from contextlib  import contextmanager
from dataclasses import dataclass
from Logging     import Metrics
from numpy       import array
from time        import time
from torch       import BoolTensor, FloatTensor, LongTensor, stack

@contextmanager
def timer():
    start = time()
    yield lambda: time() - start

@dataclass
class Experience:
    action     : int
    done       : bool
    next_state : FloatTensor
    reward     : float
    state      : FloatTensor

    def __iter__(self):
        return iter((self.state, self.action, self.next_state, self.reward, self.done))

    @staticmethod
    def batch_to_tensor(experiences, device):
        states, actions, next_states, rewards, dones = zip(*experiences)
        return Experience(
            action     = LongTensor(actions).to(device),
            done       = BoolTensor(dones).to(device),
            next_state = stack(next_states).to(device),
            reward     = FloatTensor(rewards).to(device),
            state      = stack(states).to(device)
        )

class Gymnasium:
    def __init__(self, agent, debug, emulator, logging, reward, settings):
        self.action           = None
        self.action_index     = None
        self.action_number    = 0
        self.agent            = agent
        self.current_episode  = 0
        self.current_frame    = None
        self.debug            = debug
        self.device           = agent.device
        self.elapsed_time     = None
        self.emulator         = emulator
        self.episode_done     = False
        self.logging          = logging
        self.next_frame       = None
        self.reward           = reward
        self.settings         = settings
        self.total_reward     = 0

    def finalize_episode(self):
        self.logging.save_episode_video(self.current_episode)
        self.logging.print_episode_summary(self.current_episode)

    def handle_action(self):
        if self.action == 'wait':
            self.next_frame = self.emulator.advance_frame()
            self.store_experience(reward=0, done=False)
            if self.debug:
                print("Waiting 1 tick.")
        else:
            is_effective, self.next_frame = self.emulator.press_button(self.action)
            action_reward, self.episode_done, action_type = self.reward.evaluate_action(self.current_frame, self.next_frame, is_effective)
            self.total_reward += action_reward
            self.store_experience(reward=action_reward, done=self.episode_done)
            self.log_action(action_type, is_effective, action_reward)

        self.current_frame = self.next_frame

    def log_action(self, action_type, is_effective, action_reward):
        action_loss, action_q_value = self.agent.learn_from_experience()
        self.logging.log_action(
            self.current_episode, 
            Metrics \
            (
                action        = self.action,
                action_number = self.action_number,
                action_type   = action_type,
                elapsed_time  = self.elapsed_time(),
                is_effective  = is_effective,
                loss          = action_loss,
                q_value       = action_q_value,
                reward        = action_reward,
                total_reward  = self.total_reward
            )
        )

    def run_episode(self):
        self.reset_episode_state()
        with timer() as self.elapsed_time:
            while not self.episode_done and self.action_number < self.settings.MAX_ACTIONS:
                self.current_frame = self.emulator.advance_until_playable()
                self.select_action()
                self.handle_action()
                self.action_number += 1

        self.finalize_episode()
        return self.logging.calculate_episode_metrics(self.current_episode)

    def reset_episode_state(self):
        self.action_number = 0
        self.current_frame = self.emulator.reset()
        self.episode_done  = False
        self.reward.reset()
        self.total_reward  = 0

    def select_action(self):
        self.action_index = self.agent.select_action(self.current_frame)
        self.action       = self.settings.action_space[self.action_index]

    def store_experience(self, reward, done):
        self.agent.store_experience(Experience \
        (
            action     = self.action_index,
            done       = done,
            next_state = FloatTensor(self.next_frame).to(self.device),
            reward     = reward,
            state      = FloatTensor(self.current_frame).to(self.device)
        )
    )

    def train(self, num_episodes):
        for self.current_episode in range(num_episodes):
            self.run_episode()
            self.agent.save_checkpoint(self.settings.checkpoints_directory / f"checkpoint_episode_{self.current_episode + 1}.pth")

        self.logging.plot_metrics()
        self.logging.save_metrics()
        self.emulator.close_emulator()