from Gymnasium import Gymnasium
from Hyperparameters import Hyperparameters

class Orchestrator:
    def __init__(self, rom_path, action_space, state_dim, save_dir, date):
        self.hyperparameters = Hyperparameters()
        self.gym = Gymnasium(rom_path, action_space, state_dim, save_dir, date, self.hyperparameters)

    def close(self):
        self.gym.close()

    def run(self, num_episodes):
        self.gym.run(num_episodes)

# Usage example
if __name__ == "__main__":
    rom_path = "PokemonBlue.gb"
    action_space = ['a', 'b', 'select', 'start', 'left', 'right', 'up', 'down']
    state_dim = (3, 160, 144)  # Assuming the state is a 3-channel image with dimensions (160, 144)
    save_dir = "path/to/save/directory"
    date = "YYYY-MM-DD"
    orchestrator = Orchestrator(rom_path, action_space, state_dim, save_dir, date)

    try:
        orchestrator.run(num_episodes = 100)
    except KeyboardInterrupt:
        orchestrator.close()