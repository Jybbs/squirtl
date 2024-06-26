from pathlib import Path
from torch import backends, device

class Settings:
    def __init__(self):
        self.action_space = ['wait', 'a', 'b', 'down', 'left', 'right', 'up']
        self.device               = device("mps" if backends.mps.is_available() else "cpu")
        self.state_dimensions     = (144, 160, 4)  # (height, width, channels)

        # Hyperparameters
        self.batch_size             = 64
        self.exploration_rate       = 1.0
        self.exploration_decay      = 0.9995
        self.exploration_min        = 0.05
        self.discount_factor        = 0.99
        self.learning_rate          = 0.001
        self.learning_rate_decay    = 0.9995
        self.memory_capacity        = 100000
        self.target_update_interval = 1000

        # Frame settings
        self.blank_threshold      = 0.99
        self.playable_threshold   = 5
        self.recent_frames_pool   = 50

        # Path settings
        self.base_directory        = Path('data')
        self.checkpoints_directory = self.base_directory / "checkpoints"
        self.metrics_directory     = self.base_directory / "metrics"
        self.video_directory       = self.base_directory / "videos"

        # Reward settings
        self.GOT_STARTER_ADDRESS = (0xD74B, 2) # Address for the final event of each episode

        self.BACKTRACK_PENALTY      = -10   # Constant penalty for backtracking
        self.COMPLETION_BONUS       = 10000 # Outsized reward for reaching the final event
        self.INEFFECTIVE_PENALTY    = -1    # Small penalty for actions that don't change the state
        self.MAX_ACTIONS            = 1000  # Maximum number of actions allowed per episode
        self.NEW_STATE_BONUS        = 5     # Moderate reward for exploring new states
        self.REVISIT_POINTS         = 0.1   # Very small reward for returning to visited states without immediate backtracking

        # Create directories
        self.base_directory.mkdir(parents = True, exist_ok = True)
        self.checkpoints_directory.mkdir(exist_ok = True)
        self.metrics_directory.mkdir(exist_ok = True)
        self.video_directory.mkdir(exist_ok=True)

    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        raise AttributeError(f"'Settings' object has no attribute '{name}'")