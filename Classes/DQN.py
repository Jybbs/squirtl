from torch    import prod, tensor, zeros
from torch.nn import Conv2d, Linear, Module, ReLU, Sequential

class DQN(Module):
    def __init__(self, action_count, state_dimensions):
        super(DQN, self).__init__()
        self.action_count = action_count
        self.state_dimensions = state_dimensions  # Expect (height, width, channels)

        self.convolutional_layers = Sequential(
            Conv2d(state_dimensions[2], 32, kernel_size = 8, stride = 4),
            ReLU(),
            Conv2d(32, 64, kernel_size=4, stride=2),
            ReLU(),
            Conv2d(64, 64, kernel_size=3, stride=1),
            ReLU()
        )
        
        convolution_output_size = self.get_convolution_output_size(state_dimensions)
        
        self.fully_connected_layers = Sequential(
            Linear(convolution_output_size, 512),
            ReLU(),
            Linear(512, action_count)
        )

    def get_convolution_output_size(self, shape):
        sample_input   = zeros(1, shape[2], shape[0], shape[1])  # Create a sample input tensor
        conv_output    = self.convolutional_layers(sample_input) # Pass the sample input through convolutional layers
        total_features = int(prod(tensor(conv_output.shape)))    # Calculate the total number of features
        return total_features

    def forward(self, state):
        reshaped_state = state.permute(0, 3, 1, 2) # Adjust input shape for Conv2d: (batch_size, channels, height, width)
        convolution_output = self.convolutional_layers(reshaped_state)
        flattened_output   = convolution_output.view(convolution_output.size(0), -1)
        return self.fully_connected_layers(flattened_output)