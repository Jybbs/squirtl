from torch import cuda, device

class Settings:
    def __init__(self, run_date):
        self.action_space = ['a', 'b', 'down', 'left', 'right', 'select', 'start', 'up']
        self.device               = device("cuda" if cuda.is_available() else "cpu")
        self.run_date             = run_date
        self.state_dimensions     = (4, 36, 40)  # (Channels, Height, Width)

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
        self.BACKTRACK_PENALTY         = -10
        self.EVENT_GOT_STARTER_ADDRESS = (0xD74B, 2)
        self.EVENT_GOT_STARTER_REWARD  = 1000
        self.NEW_STATE_REWARD          = 10
        self.STEP_PENALTY              = -1

    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        raise AttributeError(f"'Settings' object has no attribute '{name}'")