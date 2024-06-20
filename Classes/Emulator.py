from pyboy import PyBoy

class Emulator:
    def __init__(self, rom_path):
        self.pyboy  = PyBoy(rom_path, sound_emulated = True, window = "SDL2")
        self.screen = self.pyboy

    def check_event_flag(self, event_address, bit_position):
        event_value = self.pyboy.get_memory_value(event_address)
        return (event_value >> bit_position) & 1 == 1

    def close(self):
        self.pyboy.stop()

    def get_screen_image(self):
        return self.pyboy.screen.ndarray

    def press_button(self, button, ticks = 1):
        self.pyboy.button(button, ticks)
