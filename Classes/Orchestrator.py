from Gymnasium import Gymnasium

class Orchestrator:
    def __init__(self, rom_path, action_space):
        self.gym = Gymnasium(rom_path, action_space)

    def close(self):
        self.gym.close()

    def run(self):
        self.gym.run()

# Usage example
if __name__ == "__main__":
    rom_path     = "PokemonBlue.gb"
    action_space = ['a', 'b', 'start', 'left', 'right', 'up', 'down']
    orchestrator = Orchestrator(rom_path, action_space)
    
    try:
        orchestrator.run()
    except KeyboardInterrupt:
        orchestrator.close()
