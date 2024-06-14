class Settings:
    def __init__(self, run_date):
        self.action_space     = ['a', 'b', 'select', 'start', 'left', 'right', 'up', 'down']
        self.run_date         = run_date
        self.save_directory   = "path/to/save/directory"
        self.state_dimensions = (36, 40, 3)
        
        self.hyperparameters = {
            "batch_size"             : 64,
            "burnin"                 : 500,
            "deque_size"             : 100000,
            "exploration_rate"       : 0.3,
            "exploration_rate_decay" : 0.99,
            "exploration_rate_min"   : 0.01,
            "gamma"                  : 0.99,
            "learn_every"            : 1,
            "learning_rate"          : 0.0001,
            "learning_rate_decay"    : 0.9999,
            "save_every"             : 10000,
            "sync_every"             : 1000
        }