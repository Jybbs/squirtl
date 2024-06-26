import torch.nn as nn

class DQN(nn.Module):
    def __init__(self, action_count, state_dimensions):
        super(DQN, self).__init__()
        self.action_count     = action_count
        self.state_dimensions = state_dimensions  # Expect (height, width, channels)

        self.network = nn.Sequential(
            nn.Conv2d(state_dimensions[2], 32, kernel_size = 8, stride = 4),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size = 4, stride = 2),
            nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size = 3, stride = 1),
            nn.ReLU(),
            nn.Flatten(),
            nn.LazyLinear(512),
            nn.ReLU(),
            nn.Linear(512, action_count)
        )

    def forward(self, state):
        return self.network(self.preprocess_state(state))

    def preprocess_state(self, state):
        if state.dim() == 3:
            state = state.unsqueeze(0)  # Add batch dimension if it's missing
        if state.size(1) != self.state_dimensions[2]:
            state = state.permute(0, 3, 1, 2)
        return state