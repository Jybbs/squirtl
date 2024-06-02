from Agent           import Agent
from Emulator        import Emulator
from Gymnasium       import Gymnasium
from Hyperparameters import Hyperparameters
from Metrics         import Metrics

class Orchestrator:
    def __init__(self, action_space, date, rom_path, save_dir, state_dim):
        self.gym = Gymnasium \
        (
            agent    = Agent(state_dim, action_space, save_dir, date, Hyperparameters()), 
            emulator = Emulator(rom_path), 
            metrics  = Metrics(save_dir)
        )

    def close(self):
        self.gym.close()

    def run(self, num_episodes):
        self.gym.run(num_episodes)

# Usage example
if __name__ == "__main__":
    orchestrator = Orchestrator(
        action_space = ['a', 'b', 'select', 'start', 'left', 'right', 'up', 'down'],
        date         = "YYYY-MM-DD",
        rom_path     = "PokemonBlue.gb",
        save_dir     = "path/to/save/directory",
        state_dim    = (3, 160, 144)
    )

    try:
        orchestrator.run(num_episodes = 100)
    except KeyboardInterrupt:
        orchestrator.close()
