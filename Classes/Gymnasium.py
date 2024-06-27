from contextlib  import contextmanager
from dataclasses import astuple, dataclass
from Logging     import Metrics
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
        return iter(astuple(self))

    @staticmethod
    def batch_to_tensor(experiences, device):
        batch = list(zip(*experiences))
        return Experience \
        (
            action     = LongTensor(batch[0]).to(device),
            done       = BoolTensor(batch[1]).to(device),
            next_state = stack(batch[2]).to(device),
            reward     = FloatTensor(batch[3]).to(device),
            state      = stack(batch[4]).to(device)
        )

class Gymnasium:
    def __init__(self, agent, emulator, logging, reward, settings):
        self.agent    = agent
        self.device   = settings.device
        self.emulator = emulator
        self.logging  = logging
        self.reward   = reward
        self.settings = settings
        self.reset_episode_state()

    def finalize_episode(self):
        return self.logging.log_episode()

    def handle_action(self, get_elapsed_time):
        if self.action == 'wait':
            is_effective    = False
            self.next_frame = self.emulator.advance_frame()
        else:
            is_effective, self.next_frame = self.emulator.press_button(self.action)

        reward, done, action_type = self.reward.evaluate_action(self.current_frame, self.next_frame, is_effective, self.action)
        self.episode_done  = done
        self.total_reward += reward

        self.store_and_learn \
        (
            action_type      = action_type,
            done             = done,
            get_elapsed_time = get_elapsed_time,
            is_effective     = is_effective,
            reward           = reward
        )
        self.current_frame = self.next_frame

    def reset_episode_state(self):
        self.action        = None
        self.action_index  = None
        self.action_number = 0
        self.current_frame = None
        self.episode_done  = False
        self.next_frame    = None
        self.total_reward  = 0

    def run_episode(self):
        self.reset_episode_state()
        self.current_frame = self.emulator.reset()
        self.reward.reset()

        with timer() as get_elapsed_time:
            while not self.episode_done and self.action_number < self.settings.MAX_ACTIONS:
                self.action_index  = self.agent.select_action(self.current_frame)
                self.action        = self.settings.action_space[self.action_index]
                self.current_frame = self.emulator.advance_until_playable()
                
                self.handle_action(get_elapsed_time)
                self.action_number += 1

        return self.finalize_episode()

    def store_and_learn(self, action_type, done, get_elapsed_time, is_effective, reward):
        self.agent.store_experience(
            Experience \
            (
                action     = self.action_index,
                done       = done,
                next_state = FloatTensor(self.next_frame).to(self.device),
                reward     = reward,
                state      = FloatTensor(self.current_frame).to(self.device)
            )
        )
        
        action_loss, action_q_value = self.agent.learn_from_experience()
        
        self.logging.log_action(
            Metrics \
            (
                action        = self.action,
                action_number = self.action_number,
                action_type   = action_type,
                elapsed_time  = get_elapsed_time(),
                is_effective  = is_effective,
                loss          = action_loss,
                q_value       = action_q_value,
                reward        = reward,
                total_reward  = self.total_reward
            )
        )

    def train(self, num_episodes, start_episode = 1):
        print(f"\n{'='*50}")
        print(f"Starting training from episode {start_episode}")
        print(f"{'='*50}\n")

        if start_episode > 1:
            checkpoint_path = self.settings.checkpoints_directory / f"checkpoint_episode_{start_episode - 1}.pth"
            self.agent.load_checkpoint(checkpoint_path)

        for episode in range(start_episode, start_episode + num_episodes):
            print(f"\nRunning episode {episode}...")
            self.run_episode()
            self.agent.save_checkpoint(self.settings.checkpoints_directory / f"checkpoint_episode_{episode}.pth")

        print(f"\n{'='*50}")
        print(f"Training completed. Total episodes: {start_episode + num_episodes - 1}")
        print(f"{'='*50}\n")

        self.emulator.close_emulator()