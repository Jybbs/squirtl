class Hyperparameters:
    def __init__(self):
        self.exploration_rate = 1.0
        self.exploration_rate_decay = 0.99
        self.exploration_rate_min = 0.1
        self.deque_size = 10000
        self.batch_size = 32
        self.gamma = 0.99
        self.learning_rate = 0.00025
        self.learning_rate_decay = 0.99
        self.burnin = 1000
        self.learn_every = 3
        self.sync_every = 1000
        self.save_every = 5000