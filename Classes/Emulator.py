from numpy import array, array_equal
from pyboy import PyBoy

class Emulator:
    def __init__(self, debug, frames, rom_path, settings, episode):
        self.debug           = debug
        self.frames          = frames
        self.previous_values = {}
        self.rom_path        = rom_path
        self.settings        = settings
        self.pyboy           = self.initialize_pyboy()
        self.episode         = episode

    def advance_frame(self, frames = 4):
        for _ in range(frames):
            self.pyboy.tick()
        return self.get_screen_data()

    def advance_until_playable(self):
        while not self.frames.is_playable_state(self.get_screen_data()):
            self.advance_frame()
        return self.get_screen_data()

    def check_event_flag(self, event_address, bit_position = None):
        current_value  = self.pyboy.memory[event_address]
        previous_value = self.previous_values.get(event_address, current_value)
        self.previous_values[event_address] = current_value

        if bit_position is not None:
            previous_bit = (previous_value >> bit_position) & 1
            current_bit  = (current_value >> bit_position) & 1
            return previous_bit == 0 and current_bit == 1
        else:
            return previous_value == 0 and current_value == 1

    def close_emulator(self):
        self.pyboy.stop()

    def get_screen_data(self):
        frame = array(self.pyboy.screen.ndarray, copy = True)
        self.frames.add(frame, self.episode)
        return frame

    def initialize_pyboy(self):
        pyboy = PyBoy(self.rom_path, 
                      window = "SDL2" if self.debug else "null")
        pyboy.set_emulation_speed(0)
        return pyboy

    def press_button(self, action):
        action.current_frame = self.get_screen_data()
        
        if action.action_index != 0:
            self.pyboy.button(self.settings.action_space[action.action_index], delay = 2)
        else:
            pass

        self.advance_frame()
        
        action.next_frame   = self.get_screen_data()
        action.is_effective = not array_equal(action.current_frame, action.next_frame)

    def reset(self):
        self.close_emulator()
        self.frames.reset()
        self.pyboy = self.initialize_pyboy()
        return self.get_screen_data()

    def set_episode(self, episode):
        self.episode = episode