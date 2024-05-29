from Emulator import Emulator
from PPOAgent import PPOAgent

class Gymnasium:
    def __init__(self, rom_path, action_space):
        self.emulator = Emulator(rom_path)
        self.agent = PPOAgent(action_space)

    def run(self):
        try:
            while True:
                action = self.agent.select_action()  # PPO agent selects action
                self.emulator.press_button(action)
        except KeyboardInterrupt:
            self.close()

    def close(self):
        self.emulator.close()
