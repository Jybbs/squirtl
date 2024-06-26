from collections import deque
from itertools   import islice
from numpy       import bincount, array_equal, sum
class Frames:
    def __init__(self, settings):
        self.settings = settings
        self.explored_frames = []
        self.recent_frames = deque(maxlen = self.settings.recent_frames_pool)

    def add(self, frame):
        self.recent_frames.append(frame)

    def add_explored(self, frame):
        self.explored_frames.append(frame)
        
    def get_episode_frames(self):
        return self.current_episode_frames
    
    def is_backtracking(self, frame):
        return any(array_equal(frame, f) for f in islice(self.recent_frames, 
                                                            max(0, len(self.recent_frames) - self.settings.backtrack_window), 
                                                            None))

    def is_new_state(self, frame):
        return not any(array_equal(frame, f) for f in self.explored_frames)

    def is_blank_screen(self, frame):
        flat_frame = frame.flatten()
        most_common_pixel = bincount(flat_frame).argmax()
        return sum(flat_frame == most_common_pixel) / flat_frame.size > self.settings.blank_threshold

    def is_playable_state(self, frame):
        return not self.is_blank_screen(frame) and sum(array_equal(frame, f) for f in self.recent_frames) >= self.settings.playable_threshold

    def reset_all(self):
        self.explored_frames.clear()
        self.recent_frames.clear()

    def reset_episode(self):
        self.recent_frames.clear()