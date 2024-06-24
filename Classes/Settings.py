from pathlib import Path
from torch import backends, device

class Settings:
    def __init__(self, run_date):
        self.action_space = ['a', 'b', 'down', 'left', 'right', 'up']
        self.device               = device("mps" if backends.mps.is_available() else "cpu")
        self.state_dimensions     = (144, 160, 4)  # (height, width, channels)

        # Hyperparameters
        self.batch_size             = 32
        self.exploration_rate       = 1.0
        self.exploration_decay      = 0.99995
        self.exploration_min        = 0.01
        self.discount_factor        = 0.99
        self.learning_rate          = 0.0001
        self.learning_rate_decay    = 0.999
        self.memory_capacity        = 10000
        self.save_interval          = 1000
        self.target_update_interval = 1000

        # Reward settings
        self.EVENT_GOT_STARTER_ADDRESS = (0xD74B, 2) # Address for the final event of each episode

        self.BACKTRACK_PENALTY          = -5          # Constant penalty for backtracking
        self.COMPLETION_BONUS           = 20000       # Outsized reward for reaching the final event
        self.EXPLORATION_BONUS          = 10          # Moderate reward for exploring new states
        self.INEFFECTIVE_ACTION_PENALTY = -0.1       # Small penalty for actions that don't change the state
        self.MAX_STEPS                  = 1000        # Maximum number of steps allowed per episode
        self.REVISIT_POINTS             = 1           # Small reward for returning to visited states without immediate backtracking

        # Path settings
        self.base_directory        = Path(f"data/{run_date}")
        self.checkpoints_directory = self.base_directory / "checkpoints"
        self.metrics_directory     = self.base_directory / "metrics"

        # Create directories
        self.base_directory.mkdir(parents = True, exist_ok = True)
        self.checkpoints_directory.mkdir(exist_ok = True)
        self.metrics_directory.mkdir(exist_ok = True)

    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        raise AttributeError(f"'Settings' object has no attribute '{name}'")