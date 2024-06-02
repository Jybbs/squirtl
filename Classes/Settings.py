class Settings:
    def __init__(self):
        self.action_space     = ['a', 'b', 'select', 'start', 'left', 'right', 'up', 'down']
        self.run_date         = "YYYY-MM-DD"
        self.save_directory   = "path/to/save/directory"
        self.state_dimensions = (3, 160, 144)
        
        self.hyperparameters = {
            "batch_size"             : 32,
            "burnin"                 : 1000,
            "deque_size"             : 10000,
            "exploration_rate"       : 1.0,
            "exploration_rate_decay" : 0.99,
            "exploration_rate_min"   : 0.1,
            "gamma"                  : 0.99,
            "learn_every"            : 3,
            "learning_rate"          : 0.00025,
            "learning_rate_decay"    : 0.99,
            "save_every"             : 5000,
            "sync_every"             : 1000
        }
