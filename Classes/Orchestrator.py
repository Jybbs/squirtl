from Agent     import Agent
from Emulator  import Emulator
from Frames    import Frames
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
        self.frames   = Frames(self.settings)
        self.emulator = Emulator(self.frames, self.config['rom_path'])
        self.agent    = Agent(self.settings)
        self.logging  = Logging(self.config['debug'], self.frames, self.settings)
        self.reward   = Reward(self.emulator, self.frames, self.settings)

        self.gym = Gymnasium \
            (
                self.agent, 
                self.config['debug'], 
                self.emulator, 
                self.frames, 
                self.logging, 
                self.reward, 
                self.settings
            )

    def train(self):
        self.gym.train(self.config['num_episodes'])

if __name__ == "__main__":
    config = \
    {
        'debug'        : True,
        'num_episodes' : 5,
        'rom_path'     : "PokemonBlue.gb",
    }
    
    orchestrator = Orchestrator(config)
    orchestrator.train()