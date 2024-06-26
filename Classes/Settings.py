from pathlib import Path
from torch   import backends, device

class Settings:
    def __init__(self):
        self.setup_path_settings()
        self.create_directories()
        self.setup_action_space()
        self.setup_addresses()
        self.setup_device()
        self.setup_frame_settings()
        self.setup_hyperparameters()
        self.setup_reward_settings()
        self.setup_state_dimensions()

    def create_directories(self):
        self.base_directory.mkdir(parents = True, exist_ok = True)
        self.checkpoints_directory.mkdir(exist_ok = True)
        self.metrics_directory.mkdir(exist_ok = True)
        self.video_directory.mkdir(exist_ok = True)

    def setup_action_space(self):
        self.action_space = ['a', 'b', 'down', 'left', 'right', 'up', 'wait']

    def setup_addresses(self):
        self.GOT_STARTER    = (0xD74B, 2)
        self.INTRO_COMPLETE = 0xC20D

    def setup_device(self):
        self.device = device("mps" if backends.mps.is_available() else "cpu")

    def setup_frame_settings(self):
        self.backtrack_window   = 50
        self.blank_threshold    = 0.99
        self.playable_threshold = 5
        self.recent_frames_pool = 500

    def setup_hyperparameters(self):
        self.batch_size             = 64
        self.discount_factor        = 0.99
        self.exploration_decay      = 0.9995
        self.exploration_min        = 0.05
        self.exploration_rate       = 1.0
        self.learning_rate          = 0.001
        self.learning_rate_decay    = 0.9995
        self.memory_capacity        = 100000
        self.target_update_interval = 1000

    def setup_path_settings(self):
        self.base_directory        = Path('data')
        self.checkpoints_directory = self.base_directory / "checkpoints"
        self.metrics_directory     = self.base_directory / "metrics"
        self.video_directory       = self.base_directory / "videos"

    def setup_reward_settings(self):
        self.BACKTRACK_PENALTY   = -10  # Constant penalty for backtracking
        self.COMPLETION_BONUS    = 1000 # Outsized reward for reaching the final event
        self.INEFFECTIVE_PENALTY = -1   # Small penalty for actions that don't change the state
        self.INTRO_BONUS         = 100  # Large reward for completing the naming process in the intro
        self.MAX_ACTIONS         = 1000 # Maximum number of actions allowed per episode
        self.NEW_STATE_BONUS     = 5    # Moderate reward for exploring new states
        self.REVISIT_POINTS      = 0.1  # Very small reward for returning to visited states without immediate backtracking

    def setup_state_dimensions(self):
        self.state_dimensions = (144, 160, 4)  # (height, width, channels)

    def __getattr__(self, name):
        raise AttributeError(f"'Settings' object has no attribute '{name}'")