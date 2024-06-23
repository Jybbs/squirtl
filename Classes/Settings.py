from torch import cuda, device

class Settings:
    def __init__(self, run_date):
        self.action_space = ['a', 'b', 'down', 'left', 'right', 'select', 'start', 'up']
        self.device               = device("cuda" if cuda.is_available() else "cpu")
        self.run_date             = run_date
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

        self.BACKTRACK_PENALTY         = -5          # Constant penalty for backtracking
        self.COMPLETION_BONUS          = 20000       # Outsized reward for reaching the final event
        self.EXPLORATION_BONUS         = 10          # Moderate reward for exploring new states
        self.MAX_STEPS                 = 1000        # Maximum number of steps allowed per episode
        self.REVISIT_POINTS            = 1           # Small reward for returning to visited states without immediate backtracking

    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        raise AttributeError(f"'Settings' object has no attribute '{name}'")