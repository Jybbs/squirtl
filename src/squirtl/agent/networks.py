"""
Defines `QNetwork`, the network the agent trains as its online network and
copies into its target network.
"""

from collections.abc  import Mapping
from gymnasium.spaces import Dict, flatten_space
from torch            import Tensor, cat, uint8, zeros
from torch.nn         import Conv2d, Flatten, LazyConv2d, LazyLinear, Linear, Module, ModuleDict, ReLU, Sequential


class QNetwork(Module):
    """
    The Q-network the agent trains, which reads each entry of a `Dict`
    observation through its own encoder and concatenates the encodings
    before its head, as Pleines et al. do, with Mnih et al.'s convolutions
    and head and no batch normalization. Each entry stacks along its first
    axis, so at the default settings an observation holds a `(4, 72, 80)`
    stack of frames, a `(1, 48, 48)` grid, and a `(1, 4)` vector of flags.
    """

    def __init__(self, actions: int, space: Dict):
        """
        Builds an encoder per entry `space` declares and the head, then runs
        an observation of zeros through them, which sets each lazy layer's
        depth and width.
        """
        super().__init__()

        self.encoders = ModuleDict(
            {key: self.encoder(entry.shape) for key, entry in space.items()}
        )
        self.head  = Sequential(LazyLinear(512), ReLU(), Linear(512, actions))
        self.highs = {
            key: float(flatten_space(entry).high.max()) for key, entry in space.items()
        }

        self({key: zeros(1, *entry.shape, dtype=uint8) for key, entry in space.items()})

    @staticmethod
    def encoder(shape: tuple[int, ...]) -> Sequential:
        """
        Builds Mnih et al.'s three convolutions for a stack of images,
        its depth read as channels, or for a stack of vectors one fully
        connected layer of 64 units, the width Pleines et al.'s published
        configuration gives.

        Raises:
            ValueError: Where `shape` is neither stack.
        """
        match shape:
            case (_, _, _):
                return Sequential(
                    LazyConv2d(32, 8, stride=4),
                    ReLU(),
                    Conv2d(32, 64, 4, stride=2),
                    ReLU(),
                    Conv2d(64, 64, 3),
                    ReLU(),
                    Flatten()
                )
            case (_, _): return Sequential(Flatten(), LazyLinear(64), ReLU())
            case _:
                raise ValueError(
                    f"an entry of shape {shape} is neither a stack of images nor "
                    f"a stack of vectors"
                )

    def forward(self, observations: Mapping[str, Tensor]) -> Tensor:
        """
        Scales each entry into the unit interval by the bound its space
        declares, as CleanRL's `dqn_atari.py` scales frames, before its
        encoder reads it.
        """
        return self.head(
            cat(
                [
                    encoder(observations[key] / self.highs[key])
                    for key, encoder in self.encoders.items()
                ],
                1
            )
        )
