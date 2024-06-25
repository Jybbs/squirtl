from collections import deque

class Reward:
    def __init__(self, settings, emulator):
        self.action_count     = 0
        self.cumulative_score = 0
        self.emulator         = emulator
        self.explored_states  = set()
        self.recent_states    = deque(maxlen = 10)
        self.settings         = settings

    def calculate_completion_bonus(self):
        speed_bonus = max(0, self.settings.ACTIONS - self.action_count)
        return self.settings.COMPLETION_BONUS + speed_bonus

    def evaluate_action(self, current_state_hash, next_state_hash, action_effective):
        self.action_count += 1

        if self.emulator.check_event_flag(*self.settings.EVENT_GOT_STARTER_ADDRESS):
            completion_bonus = self.calculate_completion_bonus()
            self.cumulative_score += completion_bonus
            return completion_bonus, True

        if not action_effective:
            points = self.settings.INEFFECTIVE_ACTION_PENALTY

        elif self.is_unexplored_state(next_state_hash):
            self.explored_states.add(next_state_hash)
            self.recent_states.append(next_state_hash)
            points = self.settings.EXPLORATION_BONUS

        elif self.is_backtracking(current_state_hash):
            points = self.settings.BACKTRACK_PENALTY

        else:
            points = self.settings.REVISIT_POINTS

        self.cumulative_score += points
        return points, False

    def is_unexplored_state(self, state_hash):
        return state_hash not in self.explored_states

    def is_backtracking(self, state_hash):
        return state_hash in self.recent_states

    def get_episode_score(self):
        return self.cumulative_score

    def reset(self):
        self.explored_states.clear()
        self.recent_states.clear()
        self.action_count = 0
        self.cumulative_score = 0