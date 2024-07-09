from collections import Counter
from dataclasses import asdict, dataclass, field
from gym         import Env
from gym.spaces  import Box, Discrete
from numpy       import empty, ndarray, uint8
from time        import perf_counter
from typing      import List

@dataclass
class Action:
    action_index  : int     = field(default = -1)
    action_type   : str     = field(default = "initial")
    current_frame : ndarray = field(default_factory = lambda: empty((144, 160, 4), dtype = uint8))
    done          : bool    = field(default = False)
    is_effective  : bool    = field(default = True)
    loss          : float   = field(default = 0.0)
    next_frame    : ndarray = field(default_factory = lambda: empty((144, 160, 4), dtype = uint8))
    q_value       : float   = field(default = 0.0)
    reward        : float   = field(default = 0.0)
    timestamp     : float   = field(default_factory = perf_counter)
    total_reward  : float   = field(default = 0.0)

@dataclass
class Episode:
    actions        : List[Action]  = field(default_factory = list)
    frames         : List[ndarray] = field(default_factory = list)
    episode_number : int           = field(default = 1)

    @property
    def action_type_counts(self):
        return Counter(a.action_type for a in self.actions)

    @property
    def average_loss(self):
        return sum(a.loss for a in self.actions) / self.total_actions if self.actions else 0.0

    @property
    def average_q_value(self):
        return sum(a.q_value for a in self.actions) / self.total_actions if self.actions else 0.0
    
    @property
    def average_reward(self):
        return sum(a.reward for a in self.actions) / self.total_actions if self.actions else 0.0

    @property
    def current_frame(self):
        return self.actions[-1].next_frame if self.actions else None

    @property
    def done(self):
        return self.actions[-1].done if self.actions else False

    @property
    def effective_actions(self):
        return sum(a.is_effective for a in self.actions)

    @property
    def elapsed_time(self):
        return self.actions[-1].timestamp - self.actions[0].timestamp if self.actions else 0.0

    @property
    def total_actions(self):
        return len(self.actions)

    @property
    def total_reward(self):
        return self.actions[-1].total_reward if self.actions else 0.0

    def add_action(self, action):
        self.actions.append(action)

    def add_frame(self, frame):
        self.frames.append(frame)

    def increment(self):
        self.episode_number += 1
        self.reset()

    def reset(self):
        self.actions.clear()
        self.frames.clear()

from gym        import Env
from gym.spaces import Box, Discrete
from numpy      import uint8

class Gymnasium(Env):
    def __init__(self, agent, emulator, logging, reward, settings):
        super().__init__()
        self.action_space      = Discrete(len(settings.action_space))
        self.agent             = agent
        self.emulator          = emulator
        self.episode           = Episode()
        self.logging           = logging
        self.observation_space = Box(low = 0, high = 255, shape = (144, 160, 4), dtype = uint8)
        self.reward            = reward
        self.settings          = settings

    def __call__(self):
        self.reset()
        self.logging(self.episode)
        while not self.episode.done:
            action_index = self.agent.select_action(self.episode.current_frame)
            self.step(action_index)
        self.logging.log_episode()

    def load_checkpoint(self, episode):
        checkpoint_path = self.settings.checkpoints_directory / f"checkpoint_{(episode - 1):04d}.pth"
        self.agent.load_checkpoint(checkpoint_path)

    def reset(self):
        self.episode.reset()
        self.emulator.set_episode(self.episode)
        initial_frame = self.emulator.reset()
        self.episode.add_frame(initial_frame)
        self.reward.reset()
        return self.episode.current_frame

    def run_training_session(self, num_episodes, start_episode):
        self.episode.episode_number = start_episode
        if start_episode > 1:
            self.load_checkpoint(start_episode)

        for _ in range(num_episodes):
            print(f"\nRunning episode {self.episode.episode_number} of {start_episode + num_episodes - 1}")
            self()
            self.save_checkpoint(self.episode.episode_number)
            self.episode.increment()

        self.emulator.close_emulator()

    def save_checkpoint(self, episode):
        checkpoint_path = self.settings.checkpoints_directory / f"checkpoint_{episode:04d}.pth"
        self.agent.save_checkpoint(checkpoint_path, self.episode.total_actions)

    def step(self, action_index):
        action = Action(action_index = action_index, current_frame = self.emulator.advance_until_playable())
        
        self.emulator.press_button(action)
        self.reward.evaluate_action(action, self.episode.total_actions)
        action.total_reward = self.episode.total_reward + action.reward
        
        self.agent.store_action(action)
        self.agent.learn(action)
        self.agent.update_target_network(self.episode.total_actions)
        
        self.episode.add_action(action)
        self.logging.log_action(action)

        if self.episode.total_actions >= self.settings.MAX_ACTIONS:
            action.done = True

        return action.next_frame, action.reward, action.done, vars(action)