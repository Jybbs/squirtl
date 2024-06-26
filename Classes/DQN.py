import torch
import torch.nn as nn
import torch.nn.functional as F

class DQN(nn.Module):
    def __init__(self, action_count, state_dimensions):
        super(DQN, self).__init__()
        self.action_count = action_count
        self.state_dimensions = state_dimensions  # Expect (height, width, channels)

        self.convolutional_layers = nn.Sequential(
            nn.Conv2d(state_dimensions[2], 32, kernel_size = 8, stride = 4),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size = 4, stride = 2),
            nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size = 3, stride = 1),
            nn.ReLU()
        )
        
        convolution_output_size = self.get_convolution_output_size()
        
        self.fully_connected_layers = nn.Sequential(
            nn.Linear(convolution_output_size, 512),
            nn.ReLU(),
            nn.Linear(512, action_count)
        )

    def forward(self, state):
        state = self.preprocess_state(state)
        convolution_output = self.convolutional_layers(state)
        flattened_output   = convolution_output.view(convolution_output.size(0), -1)
        return self.fully_connected_layers(flattened_output)

    def get_convolution_output_size(self):
        sample_input       = torch.zeros(1, self.state_dimensions[2], self.state_dimensions[0], self.state_dimensions[1])
        convolution_output = self.convolutional_layers(sample_input)
        return int(torch.prod(torch.tensor(convolution_output.size())))

    def preprocess_state(self, state):
        if state.dim() == 3:
            state = state.unsqueeze(0)  # Add batch dimension if it's missing
        if state.size(1) != self.state_dimensions[2]:
            state = state.permute(0, 3, 1, 2)
        return state