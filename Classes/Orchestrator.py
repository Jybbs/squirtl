from Agent     import Agent
from Emulator  import Emulator
from Gymnasium import Gymnasium
from Metrics   import Metrics
from Reward    import Reward
from Settings  import Settings

class Orchestrator:
    def __init__(self, rom_path, run_date):
        self.emulator = Emulator(rom_path)
        self.settings = Settings(run_date)
        self.gym = Gymnasium \
            (
                agent    = Agent(self.settings), 
                emulator = self.emulator, 
                metrics  = Metrics(self.settings.save_directory),
                reward   = Reward(self.emulator)
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
            rom_path = "PokemonBlue.gb",
            run_date = "2024-06-13",
        )

    orchestrator.run(num_episodes = 1000)
