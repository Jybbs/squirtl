class Reward:
    def __init__(self, settings, emulator):
        self.emulator       = emulator
        self.settings       = settings
        self.visited_states = set()

    def calculate_reward(self, current_state, next_state):
        if self.emulator.check_event_flag(*self.settings.EVENT_GOT_STARTER_ADDRESS):
            return self.settings.EVENT_GOT_STARTER_REWARD, True

        if next_state not in self.visited_states:
            self.visited_states.add(next_state)
            return self.settings.NEW_STATE_REWARD, False

        if current_state in self.visited_states:
            return self.settings.BACKTRACK_PENALTY, False

        return self.settings.STEP_PENALTY, False