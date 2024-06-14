import numpy as np

class Reward:
    def __init__(self, emulator):
        self.emulator = emulator
        self.event_got_starter = False
        self.event_memory_addresses = {
            'EVENT_GOT_STARTER': (0xD74B, 2)  # Memory address and bit position
        }
        self.visited_states = set()

    def calculate_reward(self, state, next_state):
        if self.check_event_flag('EVENT_GOT_STARTER'):
            self.event_got_starter = True
            return 1000  # Large positive reward for reaching the target event

        # Check if the next state has been visited before
        if next_state not in self.visited_states:
            self.visited_states.add(next_state)
            return 10  # Small positive reward for visiting a new state

        # Check if the agent has backtracked to a previously visited state
        if state in self.visited_states:
            return -10  # Negative reward for backtracking

        return -1  # Small negative reward for each step

    def check_event_flag(self, event_name):
        event_address, bit_position = self.event_memory_addresses[event_name]
        event_value = self.emulator.pyboy.get_memory_value(event_address)
        return (event_value >> bit_position) & 1 == 1