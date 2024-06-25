from numpy import array, array_equal
from pyboy import PyBoy

class Emulator:
    def __init__(self, frames, rom_path):
        self.frames         = frames
        self.pyboy_instance = PyBoy(rom_path, window = "SDL2")
        self.rom_path       = rom_path

        self.pyboy_instance.set_emulation_speed(0)

    def check_event_flag(self, event_address, bit_position):
        event_value = self.pyboy_instance.memory[event_address]
        return (event_value >> bit_position) & 1 == 1

    def close_emulator(self):
        self.pyboy_instance.stop()

    def get_screen_data(self):
        frame = array(self.pyboy_instance.screen.ndarray, copy = True)
        self.frames.add(frame)
        return frame

    def advance_until_playable(self):
        while True:
            current_frame = self.get_screen_data()
            if self.frames.is_playable_state(current_frame):
                return current_frame
            self.pyboy_instance.tick()

    def press_button(self, button, frames = 2):
        initial_frame = self.get_screen_data()
        self.pyboy_instance.button(button, delay = frames)
        
        for _ in range(frames):
            self.pyboy_instance.tick()
        
        new_frame    = self.get_screen_data()
        is_effective = not array_equal(initial_frame, new_frame)
        return is_effective, new_frame

    def reset_emulator(self):
        self.close_emulator()
        self.pyboy_instance = PyBoy(self.rom_path, window = "SDL2")
        self.frames.reset_all()
        return self.get_screen_data()