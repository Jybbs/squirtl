from Agent           import Agent
from BPCA.CythonBPCA import CythonBPCA
from Emulator        import Emulator
from Frames          import Frames
from Gymnasium       import Gymnasium
from Logging         import Logging
from Reward          import Reward
from Settings        import Settings

class Orchestrator:
    def __init__(self, config):
        self.config   = config
        self.settings = Settings()
        self.bpca     = self.initialize_bpca()
        self.setup_components()

    def initialize_bpca(self):
        if self.config.get('bpca', False):
            return CythonBPCA \
            (
                self.settings.bpca_block_size, 
                self.settings.bpca_num_components, 
                *self.settings.state_dimensions
            )
        return None

    def setup_components(self):
        self.frames   = Frames(self.settings, self.bpca)
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
        self.gym.train(self.config['num_episodes'], self.config['start_episode'])

if __name__ == "__main__":
    config = {
        'bpca'          : False,
        'debug'         : True,
        'num_episodes'  : 1,
        'rom_path'      : "PokemonBlue.gb",
        'start_episode' : 7
    }
    
    orchestrator = Orchestrator(config)
    orchestrator.train()