from contextlib  import contextmanager
from dataclasses import dataclass
from time        import time

@contextmanager
def timer():
    start = time()
    yield lambda: time() - start

@dataclass
class Metrics:
    action        : str
    action_number : int
    action_type   : str
    elapsed_time  : float
    is_effective  : bool
    loss          : float
    q_value       : float
    reward        : float
    total_reward  : float

class Gymnasium:
    def __init__(self, agent, emulator, logging, reward, settings):
        self.agent    = agent
        self.emulator = emulator
        self.logging  = logging
        self.reward   = reward
        self.settings = settings

    def load_checkpoint(self, start_episode):
        checkpoint_path = self.settings.checkpoints_directory / f"checkpoint_episode_{start_episode - 1}.pth"
        self.agent.load_checkpoint(checkpoint_path)

    def log_action_metrics(self, action_type, get_elapsed_time, loss, q_value, reward):
        metrics = Metrics \
        (
            action        = self.action,
            action_number = self.action_number,
            action_type   = action_type,
            elapsed_time  = get_elapsed_time(),
            is_effective  = self.is_effective,
            loss          = loss,
            q_value       = q_value,
            reward        = reward,
            total_reward  = self.total_reward
        )
        self.logging.log_action(metrics)

    def process_action_results(self, get_elapsed_time):
        reward, self.episode_done, action_type = self.reward.evaluate_action \
        (
            self.action,
            self.is_effective,
            self.next_state,
            self.state
        )

        self.total_reward += reward
        self.agent.store_experience \
        (
            action     = self.action_index,
            done       = self.episode_done,
            next_state = self.next_state,
            reward     = reward,
            state      = self.state
        )

        loss, q_value = self.agent.learn_from_experience()
        self.log_action_metrics(action_type, get_elapsed_time, loss, q_value, reward)
        self.state = self.next_state

    def reset_episode_state(self):
        self.action_number = 0
        self.episode_done  = False
        self.reward.reset()
        self.state         = self.emulator.reset()
        self.total_reward  = 0

    def run_episode(self):
        self.reset_episode_state()
        
        with timer() as get_elapsed_time:
            while not self.episode_done and self.action_number < self.settings.MAX_ACTIONS:
                self.select_and_perform_action()
                self.process_action_results(get_elapsed_time)
                self.action_number += 1

        return self.logging.log_episode()

    def save_checkpoint(self, episode):
        checkpoint_path = self.settings.checkpoints_directory / f"checkpoint_episode_{episode}.pth"
        self.agent.save_checkpoint(checkpoint_path)

    def select_and_perform_action(self):
        self.action_index = self.agent.select_action(self.state)
        self.action       = self.settings.action_space[self.action_index]
        
        self.state = self.emulator.advance_until_playable()
        self.is_effective, self.next_state = self.emulator.press_button(self.action)

    def train(self, num_episodes, start_episode = 1):
        if start_episode > 1:
            self.load_checkpoint(start_episode)

        for episode in range(start_episode, start_episode + num_episodes):
            print(f"\nRunning episode {episode}.")
            self.run_episode()
            self.save_checkpoint(episode)

        self.emulator.close_emulator()