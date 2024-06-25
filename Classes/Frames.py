from collections import deque
from itertools   import islice
from numpy       import array_equal

class Frames:
    def __init__(self):
        self.backtrack_window       = 50
        self.current_episode_frames = []
        self.explored_frames        = []
        self.playable_threshold     = 5
        self.recent_frames          = deque(maxlen = 500)

    def add(self, frame):
        self.current_episode_frames.append(frame)
        self.recent_frames.append(frame)

    def add_explored(self, frame):
        self.explored_frames.append(frame)

    def get_episode_frames(self):
        return self.current_episode_frames

    def is_backtracking(self, frame):
        return any(array_equal(frame, f) for f in islice(self.recent_frames, 
                                                         max(0, len(self.recent_frames) - self.backtrack_window), 
                                                         None))

    def is_new_state(self, frame):
        return not any(array_equal(frame, f) for f in self.explored_frames)

    def is_playable_state(self, frame):
        return sum(array_equal(frame, f) for f in self.recent_frames) >= self.playable_threshold

    def reset_all(self):
        self.current_episode_frames.clear()
        self.explored_frames.clear()
        self.recent_frames.clear()

    def reset_episode(self):
        self.current_episode_frames = []