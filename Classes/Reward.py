from collections import deque
from numpy       import array_equal

class Reward:
    def __init__(self, settings, emulator):
        self.action_count     = 0
        self.cumulative_score = 0
        self.emulator         = emulator
        self.explored_states  = []
        self.recent_states    = deque(maxlen = 10)
        self.settings         = settings

    def calculate_completion_bonus(self):
        speed_bonus = max(0, self.settings.MAX_ACTIONS - self.action_count)
        return self.settings.COMPLETION_BONUS + speed_bonus

    def evaluate_action(self, current_state, next_state, action_effective):
        self.action_count += 1

        if self.emulator.check_event_flag(*self.settings.EVENT_GOT_STARTER_ADDRESS):
            completion_bonus = self.calculate_completion_bonus()
            self.cumulative_score += completion_bonus
            return completion_bonus, True

        if not action_effective:
            points = self.settings.INEFFECTIVE_ACTION_PENALTY

        elif self.is_unexplored_state(next_state):
            self.explored_states.append(next_state)
            self.recent_states.append(next_state)
            points = self.settings.EXPLORATION_BONUS

        elif self.is_backtracking(current_state):
            points = self.settings.BACKTRACK_PENALTY

        else:
            points = self.settings.REVISIT_POINTS

        self.cumulative_score += points
        return points, False

    def is_unexplored_state(self, state):
        return not any(array_equal(state, explored_state) for explored_state in self.explored_states)

    def is_backtracking(self, state):
        return any(array_equal(state, recent_state) for recent_state in self.recent_states)

    def get_episode_score(self):
        return self.cumulative_score

    def reset(self):
        self.explored_states.clear()
        self.recent_states.clear()
        self.action_count = 0
        self.cumulative_score = 0