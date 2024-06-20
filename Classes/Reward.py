class Reward:
    BACKTRACK_PENALTY         = -10
    EVENT_GOT_STARTER_ADDRESS = (0xD74B, 2)
    EVENT_GOT_STARTER_REWARD  = 1000
    NEW_STATE_REWARD          = 10
    STEP_PENALTY              = -1

    def __init__(self, emulator):
        self.emulator = emulator
        self.visited_states = set()

    def calculate_reward(self, state, next_state):
        if self.emulator.check_event_flag(*self.EVENT_GOT_STARTER_ADDRESS):
            return self.EVENT_GOT_STARTER_REWARD, True

        if next_state not in self.visited_states:
            self.visited_states.add(next_state)
            return self.NEW_STATE_REWARD, False

        if state in self.visited_states:
            return self.BACKTRACK_PENALTY, False

        return self.STEP_PENALTY, False