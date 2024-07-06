class Reward:
    def __init__(self, emulator, frames, settings):
        self.settings          = settings
        self.action_count      = 0
        self.consecutive_waits = 0
        self.cumulative_score  = 0
        self.emulator          = emulator
        self.frames            = frames
        self.intro_completed   = False

    def calculate_action_reward(self, current_frame, next_frame, is_effective):
        if not is_effective:
            return self.settings.INEFFECTIVE_PENALTY, False, "ineffective"

        if self.frames.is_new_state(next_frame):
            self.frames.add_explored(next_frame)
            return self.settings.NEW_STATE_BONUS, False, "new"

        if self.frames.is_backtracking(current_frame):
            return self.settings.BACKTRACK_PENALTY, False, "backtrack"

        return self.settings.REVISIT_POINTS, False, "revisit"

    def calculate_completion_bonus(self):
        speed_bonus = max(0, self.settings.MAX_ACTIONS - self.action_count)
        return self.settings.COMPLETION_BONUS + speed_bonus

    def evaluate_action(self, current_frame, next_frame, is_effective, action):
        self.action_count += 1

        if self.is_game_completed():
            return self.process_game_completion()
        
        if not self.intro_completed and self.is_intro_completed():
            return self.process_intro_completion()

        reward, done, action_type = self.calculate_action_reward(current_frame, next_frame, is_effective)

        if action == 'wait':
            self.consecutive_waits += 1
            wait_penalty = self.settings.WAIT_PENALTY * self.consecutive_waits
            reward      += wait_penalty
            action_type  = 'wait'
        else:
            self.consecutive_waits = 0

        return reward, done, action_type

    def get_episode_score(self):
        return self.cumulative_score

    def is_game_completed(self):
        return self.emulator.check_event_flag(*self.settings.GOT_STARTER)
    
    def is_intro_completed(self):
        return self.emulator.check_event_flag(self.settings.INTRO_COMPLETE)

    def process_game_completion(self):
        completion_bonus = self.calculate_completion_bonus()
        self.cumulative_score += completion_bonus
        return completion_bonus, True, "completion"
    
    def process_intro_completion(self):
        self.cumulative_score += self.settings.INTRO_BONUS
        self.intro_completed   = True
        return self.settings.INTRO_BONUS, False, "intro_complete"

    def reset(self):
        self.action_count     = 0
        self.cumulative_score = 0
        self.intro_completed  = False