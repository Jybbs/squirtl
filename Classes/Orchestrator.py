from Agent     import Agent
from Emulator  import Emulator
from Gymnasium import Gymnasium
from Metrics   import Metrics
from Settings  import Settings

class Orchestrator:
    def __init__(self, rom_path):
        self.settings = Settings()
        self.gym = Gymnasium \
            (
                agent    = Agent(self.settings), 
                emulator = Emulator(rom_path), 
                metrics  = Metrics(self.settings.save_directory)
            )

    def run(self, num_episodes):
        try:
            self.gym.run(num_episodes)
        finally:
            self.gym.close()

# Usage example
if __name__ == "__main__":
    orchestrator = Orchestrator \
        (
            action_space = ['a', 'b', 'select', 'start', 'left', 'right', 'up', 'down'],
            date         = "YYYY-MM-DD",
            rom_path     = "PokemonBlue.gb",
            save_dir     = "path/to/save/directory",
            state_dim    = (3, 160, 144)
        )

    orchestrator.run(num_episodes = 100)
