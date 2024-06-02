from torch import nn

class DQN(nn.Module):
    def __init__(self, action_dimensions, state_dimensions):
        super(DQN, self).__init__()
        self.action_dimensions = action_dimensions
        self.state_dimensions  = state_dimensions

        self.model = nn.Sequential \
        (
            nn.Conv2d(in_channels = state_dimensions[0], out_channels = 32, kernel_size = 8, stride = 4),
            nn.ReLU(),
            nn.Conv2d(in_channels = 32, out_channels = 64, kernel_size = 4, stride = 2),
            nn.ReLU(),
            nn.Conv2d(in_channels = 64, out_channels = 64, kernel_size = 3, stride = 1),
            nn.ReLU(),
            nn.Flatten(),
            nn.Linear(3136, 512),
            nn.ReLU(),
            nn.Linear(512, action_dimensions)
        )

    def forward(self, state):
        return self.model(state)