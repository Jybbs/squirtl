from dataclasses import dataclass, field
from gym         import Env
from gym.spaces  import Box, Discrete
from numpy       import uint8
from time        import perf_counter

@dataclass
class Outcome:
    action_type  : str
    is_effective : bool
    loss         : float
    next_state   : list
    q_value      : float
    reward       : float

@dataclass
class State:
    action_number : int   = field(default = 0)
    episode_done  : bool  = field(default = False)
    start_time    : float = field(default_factory = perf_counter)
    state         : list  = field(default_factory = list)
    total_reward  : float = field(default = 0.0)

    def reset(self, initial_state):
        self.action_number = 0
        self.episode_done  = False
        self.start_time    = perf_counter()
        self.state         = initial_state
        self.total_reward  = 0.0

    def update(self, outcome):
        self.action_number += 1
        self.state          = outcome.next_state
        self.total_reward  += outcome.reward

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
        self.state             = State()

    def __call__(self):
        self.reset()
        while not self.state.episode_done and self.state.action_number < self.settings.MAX_ACTIONS:
            action = self.agent.select_action(self.state.state)
            self.step(action)
        return self.logging.log_episode()

    def evaluate_action(self, action_str, current_state, is_effective, next_state):
        return self.reward.evaluate_action \
        (
            action       = action_str,
            is_effective = is_effective,
            next_state   = next_state,
            state        = current_state
        )

    def learn(self):
        return self.agent.learn_from_experience()

    def load_checkpoint(self, start_episode):
        checkpoint_path = self.settings.checkpoints_directory / f"checkpoint_episode_{start_episode - 1}.pth"
        self.agent.load_checkpoint(checkpoint_path)

    def perform_action(self, action):
        action_str    = self.settings.action_space[action]
        current_state = self.emulator.advance_until_playable()
        is_effective, next_state = self.emulator.press_button(action_str)
        return action_str, is_effective, current_state, next_state

    def reset(self):
        initial_state = self.emulator.reset()
        self.state.reset(initial_state)
        self.reward.reset()
        return self.state.state

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
        action_str, is_effective, current_state, next_state = self.perform_action(action)
        reward, done, action_type = self.evaluate_action(action_str, current_state, is_effective, next_state)
        self.store_experience(action, current_state, next_state, reward, done)
        loss, q_value = self.learn()

        outcome = Outcome \
        (
            action_type  = action_type,
            is_effective = is_effective,
            loss         = loss,
            next_state   = next_state,
            q_value      = q_value,
            reward       = reward
        )
        self.state.update(outcome)

        self.logging.log_action \
        (
            action        = action_str,
            action_number = self.state.action_number,
            action_type   = action_type,
            elapsed_time  = perf_counter() - self.state.start_time,
            is_effective  = is_effective,
            loss          = loss,
            q_value       = q_value,
            reward        = reward,
            total_reward  = self.state.total_reward
        )

        return next_state, reward, done, {}

    def store_experience(self, action, current_state, next_state, reward, done):
        self.agent.store_experience \
        (
            action     = action,
            done       = done,
            next_state = next_state,
            reward     = reward,
            state      = current_state
        )