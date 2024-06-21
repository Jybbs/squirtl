import torch
import torch.nn as nn

class DQN(nn.Module):
    def __init__(self, action_count, state_dimensions):
        super(DQN, self).__init__()
        self.action_count     = action_count
        self.state_dimensions = state_dimensions

        self.convolutional_layers = nn.Sequential \
        (
            nn.Conv2d(state_dimensions[0], 32, kernel_size = 8, stride = 4),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size = 4, stride = 2),
            nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size = 3, stride = 1),
            nn.ReLU()
        )
        
        convolution_output_size = self.get_convolution_output_size(state_dimensions)
        
        self.fully_connected_layers = nn.Sequential \
        (
            nn.Linear(convolution_output_size, 512),
            nn.ReLU(),
            nn.Linear(512, action_count)
        )

    def forward(self, state):
        convolution_output = self.convolutional_layers(state).view(state.size()[0], -1)
        return self.fully_connected_layers(convolution_output)
    
    def get_convolution_output_size(self, shape):
        convolution_output = self.convolutional_layers(torch.zeros(1, *shape))
        return int(torch.prod(torch.tensor(convolution_output.shape)))