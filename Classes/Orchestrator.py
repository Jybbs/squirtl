from Gymnasium import Gymnasium

class Orchestrator:
    def __init__(self, rom_path, action_space):
        self.gym = Gymnasium(rom_path, action_space)

    def run(self):
        self.gym.run()

    def close(self):
        self.gym.close()

# Usage example
if __name__ == "__main__":
    rom_path = "PokemonBlue.gb"
    action_space = ['UP', 'DOWN', 'LEFT', 'RIGHT', 'A', 'B', 'START', 'SELECT']
    orchestrator = Orchestrator(rom_path, action_space)
    
    try:
        orchestrator.run()
    except KeyboardInterrupt:
        orchestrator.close()
