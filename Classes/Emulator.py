from numpy import array_equal
from pyboy import PyBoy

class Emulator:
    def __init__(self, rom_path):
        self.pyboy_instance = PyBoy(rom_path, window = "SDL2")
        self.rom_path       = rom_path

        self.pyboy_instance.set_emulation_speed(0)

    def check_event_flag(self, event_address, bit_position):
        event_value = self.pyboy_instance.memory[event_address]
        return (event_value >> bit_position) & 1 == 1

    def close_emulator(self):
        self.pyboy_instance.stop()

    def get_screen_image(self):
        return self.pyboy_instance.screen.ndarray
    
    def hash_state(self, state):
        import hashlib
        return hashlib.sha256(state).hexdigest()

    def press_button(self, button, frames = 2):
        initial_state = self.get_screen_image()
        initial_state_hash = self.hash_state(initial_state)

        self.pyboy_instance.button(button, delay = frames)
        
        # Tick to simulate the button press and release
        for _ in range(frames):
            self.pyboy_instance.tick()
        
        new_state = self.get_screen_image()
        new_state_hash = self.hash_state(new_state)
        
        is_effective = initial_state_hash != new_state_hash
        
        return is_effective, new_state

    def reset_emulator(self):
        self.close_emulator()

        self.pyboy_instance       = PyBoy(self.rom_path, window = "SDL2")
        initial_state             = self.get_screen_image()
        self.last_effective_state = initial_state
        return initial_state