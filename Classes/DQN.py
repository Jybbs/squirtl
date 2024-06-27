import torch.nn as nn

class DQN(nn.Module):
    def __init__(self, action_count, state_dimensions):
        super(DQN, self).__init__()
        self.action_count     = action_count
        self.state_dimensions = state_dimensions  # Expect (height, width, channels)

        self.feature_extraction = nn.Sequential(
            nn.Conv2d(state_dimensions[2], 32, kernel_size = 8, stride = 4),
            nn.ReLU(),
            nn.BatchNorm2d(32),
            nn.Conv2d(32, 64, kernel_size = 4, stride = 2),
            nn.ReLU(),
            nn.BatchNorm2d(64),
            nn.Conv2d(64, 64, kernel_size = 3, stride = 1),
            nn.ReLU(),
            nn.BatchNorm2d(64),
            nn.Flatten()
        )

        self.value_stream = nn.Sequential(
            nn.LazyLinear(512),
            nn.ReLU(),
            nn.Linear(512, 1)
        )

        self.advantage_stream = nn.Sequential(
            nn.LazyLinear(512),
            nn.ReLU(),
            nn.Linear(512, action_count)
        )

    def forward(self, state):
        features   = self.feature_extraction(self.preprocess_state(state))
        values     = self.value_stream(features)
        advantages = self.advantage_stream(features)
        
        q_values = values + (advantages - advantages.mean(dim = 1, keepdim = True))
        return q_values

    def preprocess_state(self, state):
        if state.dim() == 3:
            state = state.unsqueeze(0)  # Add batch dimension if it's missing
        if state.size(1) != self.state_dimensions[2]:
            state = state.permute(0, 3, 1, 2)
        return state
