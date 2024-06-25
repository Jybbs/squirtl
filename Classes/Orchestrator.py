from Agent     import Agent
from Emulator  import Emulator
from Gymnasium import Gymnasium
from Logging   import Logging
from Reward    import Reward
from Settings  import Settings

class Orchestrator:
    def __init__(self, config):
        self.config = config
        self.setup_components()

    def setup_components(self):
        self.settings = Settings()
        self.emulator = Emulator(self.config['rom_path'])
        self.agent    = Agent(self.settings)
        self.logging  = Logging(self.settings, debug = True)
        self.reward   = Reward(self.settings, self.emulator)
        self.gym      = Gymnasium(self.settings, self.agent, self.emulator, self.logging, self.reward)

    def train(self):
        self.gym.train(self.config['num_episodes'])

if __name__ == "__main__":
    config = \
    {
        'num_episodes' : 1,
        'rom_path'     : "PokemonBlue.gb",
    }
    
    orchestrator = Orchestrator(config)
    orchestrator.train()