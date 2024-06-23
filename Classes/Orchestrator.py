from Agent     import Agent
from Emulator  import Emulator
from Gymnasium import Gymnasium
from Metrics   import Metrics
from Reward    import Reward
from Settings  import Settings

class Orchestrator:
    def __init__(self, config):
        self.config = config
        self.setup_components()

    def setup_components(self):
        self.settings = Settings(self.config['run_date'])
        self.emulator = Emulator(self.config['rom_path'])
        self.agent    = Agent(self.settings)
        self.metrics  = Metrics(self.settings, self.config['save_directory'])
        self.reward   = Reward(self.settings, self.emulator)
        self.gym      = Gymnasium(self.settings, self.agent, self.emulator, self.metrics, self.reward)

    def train(self):
        self.gym.train(self.config['num_episodes'])

if __name__ == "__main__":
    config = \
    {
        'num_episodes'   : 100,
        'rom_path'       : "PokemonBlue.gb",
        'run_date'       : "2024-06-20",
        'save_directory' : "saves"
    }
    
    orchestrator = Orchestrator(config)
    orchestrator.train()