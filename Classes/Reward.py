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
            completion_bonus       = self.calculate_completion_bonus()
            self.cumulative_score += completion_bonus
            return completion_bonus, True, "completion"

        if not is_effective:
            points      = self.settings.INEFFECTIVE_PENALTY
            action_type = "ineffective"

        elif not self.frames.has_been_seen(next_frame):
            self.frames.add_seen(next_frame)
            points      = self.settings.NEW_STATE_BONUS
            action_type = "new"

        elif self.frames.is_backtracking(current_frame):
            points      = self.settings.BACKTRACK_PENALTY
            action_type = "backtrack"

        else:
            points      = self.settings.REVISIT_POINTS
            action_type = "revisit"

        self.cumulative_score += points
        return points, False, action_type
    
    def get_episode_score(self):
        return self.cumulative_score

    def reset(self):
        self.action_count     = 0
        self.cumulative_score = 0
        self.frames.reset()