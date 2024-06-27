import numpy as np
from CPP.CythonBPCA import CythonBPCA

class BPCA:
    def __init__(self, block_size, num_components, frame_height, frame_width):
        self.cython_bpca = CythonBPCA(block_size, num_components, frame_height, frame_width)

    def fit_frames(self, frames):
        # Convert numpy arrays to list of lists if necessary
        if isinstance(frames[0], np.ndarray):
            frames = [frame.tolist() for frame in frames]
        self.cython_bpca.fit_frames(frames)

    def transform_frame(self, frame):
        # Convert numpy array to list if necessary
        if isinstance(frame, np.ndarray):
            frame = frame.tolist()
        transformed = self.cython_bpca.transform_frame(frame)
        # Convert back to numpy array
        return np.array(transformed)