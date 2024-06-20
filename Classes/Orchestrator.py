from Agent     import Agent
from Emulator  import Emulator
from Gymnasium import Gymnasium
from Metrics   import Metrics
from Reward    import Reward
from Settings  import Settings

class Orchestrator:
    def __init__(self, num_episodes, rom_path, run_date, save_directory):
        self.emulator = Emulator(rom_path)
        self.settings = Settings(run_date)
        self.gym      = Gymnasium \
            (
                agent    = Agent(self.settings, save_directory), 
                emulator = self.emulator, 
                metrics  = Metrics(save_directory),
                reward   = Reward(self.emulator)
            )

        self.gym.train(num_episodes)

if __name__ == "__main__":
    
    Orchestrator \
        (
            num_episodes   = 1000,
            rom_path       = "PokemonBlue.gb",
            run_date       = "2024-06-13",
            save_directory = "saves"
        )
