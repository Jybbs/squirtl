from dataclasses import dataclass, field
from gym         import Env
from gym.spaces  import Box, Discrete
from numpy       import uint8
from time        import perf_counter

@dataclass
class Result:
    action_type  : str
    is_effective : bool
    loss         : float
    next_frame   : list
    q_value      : float
    reward       : float

@dataclass
class Episode:
    action_number : int   = field(default = 0)
    done          : bool  = field(default = False)
    start_time    : float = field(default_factory = perf_counter)
    current_frame : list  = field(default_factory = list)
    total_reward  : float = field(default = 0.0)

    def reset(self, initial_frame):
        self.action_number = 0
        self.done          = False
        self.start_time    = perf_counter()
        self.current_frame = initial_frame
        self.total_reward  = 0.0

    def update(self, result):
        self.action_number += 1
        self.current_frame  = result.next_frame
        self.total_reward  += result.reward

class Gymnasium(Env):
    def __init__(self, agent, emulator, logging, reward, settings):
        super().__init__()
        self.action_space      = Discrete(len(settings.action_space))
        self.agent             = agent
        self.emulator          = emulator
        self.logging           = logging
        self.observation_space = Box(low = 0, high = 255, shape = (144, 160, 4), dtype = uint8)
        self.reward            = reward
        self.settings          = settings
        self.episode           = Episode()

    def __call__(self):
        self.reset()
        while not self.episode.done and self.episode.action_number < self.settings.MAX_ACTIONS:
            action = self.agent.select_action(self.episode.current_frame)
            self.step(action)
        return self.logging.log_episode()

    def evaluate_action(self, action, current_frame, next_frame, is_effective):
        return self.reward.evaluate_action(current_frame, next_frame, is_effective, action)

    def learn(self):
        return self.agent.learn()

    def load_checkpoint(self, start_episode):
        checkpoint_path = self.settings.checkpoints_directory / f"checkpoint_episode_{start_episode - 1}.pth"
        self.agent.load_checkpoint(checkpoint_path)

    def perform_action(self, action):
        action         = self.settings.action_space[action]
        current_frame  = self.emulator.advance_until_playable()
        is_effective, next_frame = self.emulator.press_button(action)
        return action, current_frame, next_frame, is_effective

    def reset(self):
        initial_frame = self.emulator.reset()
        self.episode.reset(initial_frame)
        self.reward.reset()
        return self.episode.current_frame

    def run_training_session(self, num_episodes, start_episode = 1):
        if start_episode > 1:
            self.load_checkpoint(start_episode)

        for episode in range(start_episode, start_episode + num_episodes):
            print(f"\nRunning episode {episode} of {start_episode + num_episodes - 1}")
            self()
            self.save_checkpoint(episode)

        self.emulator.close_emulator()

    def save_checkpoint(self, episode):
        checkpoint_path = self.settings.checkpoints_directory / f"checkpoint_episode_{episode}.pth"
        self.agent.save_checkpoint(checkpoint_path)

    def step(self, action):
        action, current_frame, next_frame, is_effective = self.perform_action(action)
        reward, done, action_type = self.evaluate_action(action, current_frame, next_frame, is_effective)
        self.agent.add_transition(current_frame, action, next_frame, reward, done)
        loss, q_value = self.learn()

        result = Result \
        (
            action_type  = action_type,
            is_effective = is_effective,
            loss         = loss,
            next_frame   = next_frame,
            q_value      = q_value,
            reward       = reward
        )
        self.episode.update(result)

        self.logging.log_action \
        (
            action        = action,
            action_number = self.episode.action_number,
            action_type   = action_type,
            elapsed_time  = perf_counter() - self.episode.start_time,
            is_effective  = is_effective,
            loss          = loss,
            q_value       = q_value,
            reward        = reward,
            total_reward  = self.episode.total_reward
        )

        return next_frame, reward, done, {}