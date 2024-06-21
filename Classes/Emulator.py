from pyboy import PyBoy

class Emulator:
    def __init__(self, rom_path):
        self.pyboy_instance = PyBoy(rom_path, sound_emulated = True, window = "SDL2")
        self.rom_path       = rom_path

    def check_event_flag(self, event_address, bit_position):
        event_value = self.pyboy_instance.get_memory_value(event_address)
        return (event_value >> bit_position) & 1 == 1

    def close_emulator(self):
        self.pyboy_instance.stop()

    def get_screen_image(self):
        return self.pyboy_instance.screen.ndarray

    def press_button(self, button):
        self.pyboy_instance.button(button)
        self.pyboy_instance.tick()

    def reset_emulator(self):
        self.close_emulator()
        self.pyboy_instance = PyBoy(self.rom_path, sound_emulated = True, window = "SDL2")
        return self.get_screen_image()