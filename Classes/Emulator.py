from pyboy import PyBoy

class Emulator:
    def __init__(self, rom_path):
        self.pyboy  = PyBoy(rom_path, sound_emulated = True, window = "SDL2")
        self.screen = self.pyboy

    def close(self):
        self.pyboy.stop()

    def get_screen_image(self):
        return self.pyboy.screen.ndarray

    def press_button(self, button, ticks = 1):
        self.pyboy.button(button, ticks)
        self.pyboy.tick()
        self.pyboy.tick()
