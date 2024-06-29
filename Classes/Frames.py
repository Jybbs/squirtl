import numpy as np

from collections import deque

class Frames:
    def __init__(self, settings):
        self.episode_frames   = []
        self.explored_frames  = []
        self.optimized_frames = []
        self.recent_frames    = deque(maxlen = settings.recent_frames_pool)
        self.settings         = settings

    def add(self, frame):
        self.episode_frames.append(frame)
        self.recent_frames.append(frame)

    def add_explored(self, frame):
        self.explored_frames.append(frame)

    def get_episode_frames(self):
        return self.episode_frames
    
    def get_optimized_frames(self):
        return self.optimized_frames

    def is_backtracking(self, frame):
        if not self.recent_frames:
            return False
        start         = max(0, len(self.recent_frames) - self.settings.backtrack_window)
        recent_window = np.array(list(self.recent_frames)[start:])
        return np.any(np.all(frame == recent_window, axis = (1, 2, 3)))

    def is_new_state(self, frame):
        if not self.explored_frames:
            return True
        explored_array = np.array(self.explored_frames)
        return not np.any(np.all(frame == explored_array, axis = (1, 2, 3)))

    def is_blank_screen(self, frame):
        flat_frame        = frame.flatten()
        most_common_pixel = np.bincount(flat_frame).argmax()
        return sum(flat_frame == most_common_pixel) / flat_frame.size > self.settings.blank_threshold

    def is_playable_state(self, frame):
        if self.is_blank_screen(frame) or not self.recent_frames:
            return False
        recent_array = np.array(self.recent_frames)
        return sum(np.all(frame == recent_array, axis = (1, 2, 3))) >= self.settings.playable_threshold
        
    def reset(self):
        self.episode_frames.clear()
        self.explored_frames.clear()
        self.recent_frames.clear()