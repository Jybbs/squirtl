import numpy as np
from BPCA.CythonBPCA import CythonBPCA

# Define parameters
frame_height = 144
frame_width = 160
block_size = 16
num_components = 10
num_frames = 5

# Create a BPCA instance
bpca = CythonBPCA(block_size, num_components, frame_height, frame_width)

# Generate some random frame data
frames = [np.random.rand(frame_height, frame_width) for _ in range(num_frames)]

# Fit the PCA model
bpca.fit_frames(frames)

# Transform a new frame
new_frame = np.random.rand(frame_height, frame_width)
transformed_frame = bpca.transform_frame(new_frame)

print(f"Original frame shape: {new_frame.shape}")
print(f"Transformed frame shape: {transformed_frame.shape}")
print(f"Number of blocks: {(frame_height // block_size) * (frame_width // block_size)}")
print(f"Components retained per block: {num_components}")