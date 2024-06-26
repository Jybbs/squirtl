from collections import deque
from numpy import array_equal, bincount, sum

class Frames:
    def __init__(self, settings):
        self.settings = settings
        self.frames = []
        self.recent_frames = deque(maxlen=self.settings.recent_frames_pool)

    def add(self, frame):
        self.frames.append(frame)
        self.recent_frames.append(frame)

    def has_been_seen(self, frame):
        return any(array_equal(frame, f) for f in self.frames)
    
    def is_backtracking(self, frame):
        return any(array_equal(frame, f) for f in self.recent_frames)
    
    def is_blank_screen(self, frame):
        flat_frame = frame.flatten()
        most_common_pixel = bincount(flat_frame).argmax()
        return sum(flat_frame == most_common_pixel) / flat_frame.size > self.settings.blank_threshold

    def is_playable_state(self, frame):
        return not self.is_blank_screen(frame)

    def get_episode_frames(self):
        return self.frames

    def reset(self):
        self.frames.clear()
        self.recent_frames.clear()