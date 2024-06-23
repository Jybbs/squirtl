import numpy as np

class Reward:
    def __init__(self, settings, emulator):
        self.emulator           = emulator
        self.settings           = settings
        self.explored_states    = []
        self.step_count         = 0
        self.cumulative_score   = 0

    def calculate_completion_bonus(self):
        base_bonus  = self.settings.COMPLETION_BONUS
        speed_bonus = max(0, self.settings.MAX_STEPS - self.step_count)
        return base_bonus + speed_bonus

    def evaluate_action(self, current_state, next_state):
        self.step_count += 1

        if self.emulator.check_event_flag(*self.settings.EVENT_GOT_STARTER_ADDRESS):
            completion_bonus = self.calculate_completion_bonus()
            self.cumulative_score += completion_bonus
            return completion_bonus, True

        if self.is_unexplored_state(next_state):
            self.explored_states.append(next_state)
            points = self.settings.EXPLORATION_BONUS
        elif self.is_backtracking(current_state):
            points = self.settings.BACKTRACK_PENALTY
        else:
            points = self.settings.REVISIT_POINTS

        self.cumulative_score += points
        return points, False

    def is_unexplored_state(self, state):
        for explored_state in self.explored_states:  # Check last 20 states
            if np.array_equal(state, explored_state):
                return False
        return True

    def is_backtracking(self, state):
        for explored_state in self.explored_states[-10:]:  # Check last 10 states
            if np.array_equal(state, explored_state):
                return True
        return False

    def get_episode_score(self):
        return self.cumulative_score

    def reset(self):
        self.explored_states.clear()
        self.step_count = 0
        self.cumulative_score = 0