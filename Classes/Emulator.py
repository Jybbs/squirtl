from numpy import array, array_equal
from pyboy import PyBoy

class Emulator:
    def __init__(self, frames, rom_path):
        self.frames   = frames
        self.pyboy    = PyBoy(rom_path, window = "SDL2")
        self.rom_path = rom_path

        self.pyboy.set_emulation_speed(0)

    def advance_until_playable(self):
        while True:
            current_frame = self.get_screen_data()
            if self.frames.is_playable_state(current_frame):
                return current_frame
            self.pyboy.tick()

    def check_event_flag(self, event_address, bit_position):
        event_value = self.pyboy.memory[event_address]
        return (event_value >> bit_position) & 1 == 1

    def close_emulator(self):
        self.pyboy.stop()

    def get_screen_data(self):
        frame = array(self.pyboy.screen.ndarray, copy = True)
        self.frames.add(frame)
        return frame

    def press_button(self, button, frames = 2):
        initial_frame = self.get_screen_data()
        self.pyboy.button(button, delay = frames)
        
        for _ in range(frames):
            self.pyboy.tick()
        
        new_frame    = self.get_screen_data()
        is_effective = not array_equal(initial_frame, new_frame)
        return is_effective, new_frame

    def reset(self):
        self.close_emulator()
        self.pyboy = PyBoy(self.rom_path, window = "SDL2")
        self.frames.reset()
        return self.get_screen_data()
    
    def wait(self, frames = 1):
        for _ in range(frames):
            self.pyboy.tick()
        return self.get_screen_data()