from torch    import prod, tensor, zeros
from torch.nn import Conv2d, Linear, Module, ReLU, Sequential

class DQN(Module):
    def __init__(self, action_count, state_dimensions):
        super(DQN, self).__init__()
        self.action_count     = action_count
        self.state_dimensions = state_dimensions

        self.convolutional_layers = Sequential \
        (
            Conv2d(state_dimensions[0], 32, kernel_size = 8, stride = 4),
            ReLU(),
            Conv2d(32, 64, kernel_size = 4, stride = 2),
            ReLU(),
            Conv2d(64, 64, kernel_size = 3, stride = 1),
            ReLU()
        )
        
        convolution_output_size = self.get_convolution_output_size(state_dimensions)
        
        self.fully_connected_layers = Sequential \
        (
            Linear(convolution_output_size, 512),
            ReLU(),
            Linear(512, action_count)
        )

    def forward(self, state):
        convolution_output = self.convolutional_layers(state).view(state.size()[0], -1)
        return self.fully_connected_layers(convolution_output)
    
    def get_convolution_output_size(self, shape):
        convolution_output = self.convolutional_layers(zeros(1, *shape))
        return int(prod(tensor(convolution_output.shape)))