from numpy import array, array_equal
from pyboy import PyBoy

class Emulator:
    def __init__(self, debug, frames, rom_path):
        self.debug    = debug
        self.frames   = frames
        self.rom_path = rom_path
        self.pyboy    = self.initialize_pyboy()

        self.memory_addresses = [0xc20d, 0xd3ae, 0xd3af, 0xd60c, 0xd732]
        self.memory_values = {hex(address): self.pyboy.memory[address] for address in self.memory_addresses}

    def check_memory_changes(self):
        changed_addresses = []
        for address in self.memory_addresses:
            address_hex = hex(address)
            current_value = self.pyboy.memory[address]
            if self.memory_values[address_hex] != current_value:
                changed_addresses.append((address_hex, self.memory_values[address_hex], current_value))
                self.memory_values[address_hex] = current_value
        return changed_addresses

    def advance_frame(self, frames = 4):
        for _ in range(frames):
            self.pyboy.tick()
        return self.get_screen_data()

    def advance_until_playable(self):
        while not self.frames.is_playable_state(self.get_screen_data()):
            self.advance_frame()
        return self.get_screen_data()

    def check_event_flag(self, event_address, bit_position = None):
        if bit_position is not None:
            event_value = self.pyboy.memory[event_address]
            return (event_value >> bit_position) & 1 == 1
        else:
            event_value = self.pyboy.memory[event_address]
            memory = self.check_memory_changes()

            if len(memory) > 0:
                print(memory)
            return event_value != 0

    def close_emulator(self):
        self.pyboy.stop()

    def get_screen_data(self):
        frame = array(self.pyboy.screen.ndarray, copy = True)
        self.frames.add(frame)
        return frame

    def initialize_pyboy(self):
        pyboy = PyBoy(self.rom_path, 
                      window = "SDL2" if self.debug else "null")
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