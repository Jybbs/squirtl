"""
Defines `QNetwork`, the network the agent trains as its online network and
copies into its target network.
"""

from torch    import Tensor, uint8, zeros
from torch.nn import Conv2d, Flatten, LazyLinear, Linear, ReLU, Sequential


class QNetwork(Sequential):
    """
    The network Mnih et al. read a stack of frames through, three
    convolutions and two linear layers with no batch normalization, mapping
    a `(batch, 4, 72, 80)` stack of `uint8` frames to one value per action.
    """

    def __init__(self, actions: int, shape: tuple[int, ...]):
        """
        Builds the layers for an observation of `shape`, then runs one stack
        of zeros through them, which sets the width `LazyLinear` reads.
        """
        super().__init__(
            Conv2d(shape[0], 32, 8, stride=4),
            ReLU(),
            Conv2d(32, 64, 4, stride=2),
            ReLU(),
            Conv2d(64, 64, 3),
            ReLU(),
            Flatten(),
            LazyLinear(512),
            ReLU(),
            Linear(512, actions)
        )
        self(zeros(1, *shape, dtype=uint8))

    def forward(self, observations: Tensor) -> Tensor:
        """
        Scales `observations` from `uint8` into the unit interval, as
        CleanRL's `dqn_atari.py` does, before the layers read them.
        """
        return super().forward(observations / 255)
