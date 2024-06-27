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
        self.emulator = Emulator(self.config['debug'], self.frames, self.config['rom_path'])
        self.agent    = Agent(self.settings)
        self.logging  = Logging(self.config['debug'], self.frames, self.settings)
        self.reward   = Reward(self.emulator, self.frames, self.settings)

        self.gym = Gymnasium \
            (
                self.agent, 
                self.emulator, 
                self.logging, 
                self.reward, 
                self.settings,
            )

    def train(self):
        self.gym.train(self.config['num_episodes'], self.config['start_episode'])

if __name__ == "__main__":
    config = \
    {
        'debug'         : False,
        'num_episodes'  : 50,
        'rom_path'      : "PokemonBlue.gb",
        'start_episode' : 1
    }
    
    orchestrator = Orchestrator(config)
    orchestrator.train()