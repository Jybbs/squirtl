class Reward:
    def __init__(self, emulator, frames, settings):
        self.consecutive_waits = 0
        self.emulator          = emulator
        self.frames            = frames
        self.intro_completed   = False
        self.settings          = settings

    def evaluate_action(self, action, total_actions):
        if self.is_game_completed():
            return self.process_game_completion(action, total_actions)
        
        if not self.intro_completed and self.is_intro_completed():
            return self.process_intro_completion(action)

        self.calculate_action_reward(action)

        if action.action_index == 0:
            self.consecutive_waits += 1
            wait_penalty            = self.settings.WAIT_PENALTY * self.consecutive_waits
            action.action_type      = 'wait'
            action.reward          += wait_penalty
        else:
            self.consecutive_waits = 0

    def calculate_action_reward(self, action):
        if not action.is_effective:
            action.action_type = "ineffective"
            action.reward      = self.settings.INEFFECTIVE_PENALTY

        elif self.frames.is_new_state(action.next_frame):
            self.frames.add_explored(action.next_frame)
            action.action_type = "new"
            action.reward      = self.settings.NEW_STATE_BONUS

        elif self.frames.is_backtracking(action.current_frame):
            action.action_type = "backtrack"
            action.reward      = self.settings.BACKTRACK_PENALTY

        else:
            action.action_type = "revisit"
            action.reward      = self.settings.REVISIT_POINTS

    def is_game_completed(self):
        return self.emulator.check_event_flag(*self.settings.GOT_STARTER)
    
    def is_intro_completed(self):
        return self.emulator.check_event_flag(self.settings.INTRO_COMPLETE)

    def process_game_completion(self, action, total_actions):
        action.action_type = "completion"
        action.done        = True
        action.reward      = self.settings.COMPLETION_BONUS + max(0, self.settings.MAX_ACTIONS - total_actions)
    
    def process_intro_completion(self, action):
        action.action_type   = "intro_complete"
        self.intro_completed = True
        action.reward        = self.settings.INTRO_BONUS

    def reset(self):
        self.consecutive_waits = 0
        self.intro_completed   = False