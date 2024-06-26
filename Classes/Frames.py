from collections import deque
from itertools   import islice
from numpy       import array_equal, bincount, sum

class Frames:
    def __init__(self, settings):
        self.settings      = settings
        self.all_frames    = []
        self.recent_frames = deque(maxlen = self.settings.recent_frames_pool)
        self.seen_frames   = []

    def add(self, frame):
        self.all_frames.append(frame)
        self.recent_frames.append(frame)

    def add_seen(self, frame):
        self.seen_frames.append(frame)

    def get_episode_frames(self):
        return self.all_frames

    def has_been_seen(self, frame):
        # return any(array_equal(frame, f) for f in self.seen_frames)
        return True
    
    def is_backtracking(self, frame):
        return any(array_equal(frame, f) for f in islice(self.recent_frames, 
                                                         max(0, len(self.recent_frames) - self.settings.backtrack_window), 
                                                         None))
    
    def is_blank_screen(self, frame):
        flat_frame = frame.flatten()
        most_common_pixel = bincount(flat_frame).argmax()
        return sum(flat_frame == most_common_pixel) / flat_frame.size > self.settings.blank_threshold

    def is_playable_state(self, frame):
        # return not self.is_blank_screen(frame) and self.has_been_seen(frame)
        return True

    def reset(self):
        self.all_frames.clear()
        self.recent_frames.clear()
        self.seen_frames.clear()