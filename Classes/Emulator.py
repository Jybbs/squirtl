from numpy import array, array_equal
from pyboy import PyBoy

class Emulator:
    def __init__(self, frames, rom_path):
        self.frames   = frames
        self.rom_path = rom_path
        self.pyboy    = self.initialize_pyboy()

    def advance_frame(self, frames = 4):
        for _ in range(frames):
            self.pyboy.tick()
        return self.get_screen_data()

    def advance_until_playable(self):
        while not self.frames.is_playable_state(self.get_screen_data()):
            self.advance_frame()
        return self.get_screen_data()

    def check_event_flag(self, event_address, bit_position):
        event_value = self.pyboy.memory[event_address]
        return (event_value >> bit_position) & 1 == 1

    def close_emulator(self):
        self.pyboy.stop()

    def get_screen_data(self):
        frame = array(self.pyboy.screen.ndarray, copy = True)
        self.frames.add(frame)
        return frame

    def initialize_pyboy(self):
        pyboy = PyBoy(self.rom_path, window = "SDL2")
        pyboy.set_emulation_speed(0)
        return pyboy

    def press_button(self, button, frames = 2):
        initial_frame = self.get_screen_data()
        self.pyboy.button(button, delay = frames)
        
        self.advance_frame(frames)
        
        is_effective = not array_equal(initial_frame, self.get_screen_data())
        new_frame    = self.get_screen_data()
        return is_effective, new_frame

    def reset(self):
        self.close_emulator()
        self.frames.reset()
        self.pyboy = self.initialize_pyboy()
        return self.get_screen_data()