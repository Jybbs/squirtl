from Agent     import Agent
from Emulator  import Emulator
from Frames    import Frames
from Gymnasium import Gymnasium
from Logging   import Logging
from Reward    import Reward
from Settings  import Settings

class Orchestrator:
    def __init__(self, config):
        self.config   = config
        self.settings = Settings()
        self.setup_components()

    def setup_components(self):
        self.frames   = Frames(self.settings)
        self.agent    = Agent(self.settings)
        self.emulator = Emulator(self.config['debug'], self.frames, self.config['rom_path'])
        self.logging  = Logging(self.config['debug'], self.frames, self.settings, self.config['start_episode'])
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
        self.gym.run_training_session(self.config['num_episodes'], self.config['start_episode'])

if __name__ == "__main__":
    config = \
    {
        'debug'         : True,
        'num_episodes'  : 1,
        'rom_path'      : "PokemonBlue.gb",
        'start_episode' : 1
    }
    
    orchestrator = Orchestrator(config)
    orchestrator.train()