from dataclasses import asdict, dataclass, field
from gym         import Env
from gym.spaces  import Box, Discrete
from numpy       import empty, ndarray, uint8
from time        import perf_counter

@dataclass
class Action:
    action_index  : int     = field(default = -1)
    action_name   : str     = field(default = "initial")
    action_type   : str     = field(default = "initial")
    current_frame : ndarray = field(default_factory = empty((144, 160, 4), dtype = uint8))
    done          : bool    = field(default = False)
    is_effective  : bool    = field(default = True)
    loss          : float   = field(default = 0.0)
    next_frame    : ndarray = field(default_factory = empty((144, 160, 4), dtype = uint8))
    q_value       : float   = field(default = 0.0)
    reward        : float   = field(default = 0.0)
    timestamp     : float   = field(default_factory = perf_counter)
    total_reward  : float   = field(default = 0.0)

class Episode:
    def __init__(self):
        self.actions = []
        self.reset()

    @property
    def action_count(self):
        return len(self.actions)

    @property
    def current_frame(self):
        return self.actions[-1].next_frame if self.actions else None

    @property
    def done(self):
        return self.actions[-1].done if self.actions else False

    @property
    def total_reward(self):
        return self.actions[-1].total_reward if self.actions else 0.0

    def add_action(self, action):
        self.actions.append(action)

    def reset(self):
        self.actions.clear()
        self.add_action(Action())

class Gymnasium(Env):
    def __init__(self, agent, emulator, logging, reward, settings):
        super().__init__()
        self.action_space      = Discrete(len(settings.action_space))
        self.agent             = agent
        self.emulator          = emulator
        self.episode           = Episode()
        self.last_action       = None
        self.logging           = logging
        self.observation_space = Box(low = 0, high = 255, shape = (144, 160, 4), dtype = uint8)
        self.reward            = reward
        self.settings          = settings

    def __call__(self):
        self.reset()
        while not self.episode.done and self.episode.action_count < self.settings.MAX_ACTIONS:
            action_index = self.agent.select_action(self.episode.current_frame)
            self.step(action_index)
        return self.logging.log_episode()
    
    def get_last_action(self):
        return self.last_action

    def load_checkpoint(self, start_episode):
        checkpoint_path = self.settings.checkpoints_directory / f"checkpoint_episode_{start_episode - 1}.pth"
        self.agent.load_checkpoint(checkpoint_path)

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

    def step(self, action_index):
        action_name               = self.settings.action_space[action_index]
        current_frame             = self.emulator.advance_until_playable()
        is_effective, next_frame  = self.emulator.press_button(action_name)
        reward, done, action_type = self.reward.evaluate_action(action_name, current_frame, next_frame, is_effective)
        total_reward              = self.episode.total_reward + reward
        
        action = Action \
        (
            action_index  = action_index,
            action_name   = action_name,
            action_type   = action_type,
            current_frame = current_frame,
            done          = done,
            is_effective  = is_effective,
            next_frame    = next_frame,
            reward        = reward,
            total_reward  = total_reward
        )
        
        self.last_action = action
        self.agent.store_action(action)
        self.episode.add_action(action)
        self.logging.log_action(action)

        loss, q_value  = self.agent.learn()
        action.loss    = loss
        action.q_value = q_value
        
        return next_frame, reward, done, asdict(action)