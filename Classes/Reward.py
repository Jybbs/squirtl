class Reward:
    def __init__(self, emulator, frames, settings):
        self.action_count     = 0
        self.cumulative_score = 0
        self.emulator         = emulator
        self.frames           = frames
        self.settings         = settings

    def calculate_completion_bonus(self):
        speed_bonus = max(0, self.settings.MAX_ACTIONS - self.action_count)
        return self.settings.COMPLETION_BONUS + speed_bonus

    def evaluate_action(self, current_frame, next_frame, is_effective):
        self.action_count += 1

        if self.emulator.check_event_flag(*self.settings.GOT_STARTER_ADDRESS):
            completion_bonus = self.calculate_completion_bonus()
            self.cumulative_score += completion_bonus
            return completion_bonus, True, "completion"

        if not is_effective:
            return self.settings.INEFFECTIVE_PENALTY, False, "ineffective"

        if self.frames.is_new_state(next_frame):
            self.frames.add_explored(next_frame)
            return self.settings.NEW_STATE_BONUS, False, "new"

        if self.frames.is_backtracking(current_frame):
            return self.settings.BACKTRACK_PENALTY, False, "backtrack"

        return self.settings.REVISIT_POINTS, False, "revisit"
    
    def get_episode_score(self):
        return self.cumulative_score

    def reset(self):
        self.action_count     = 0
        self.cumulative_score = 0
        self.frames.reset_episode()