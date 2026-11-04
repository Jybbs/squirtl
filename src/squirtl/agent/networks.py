"""
Defines the networks the agents train, `QNetwork`, which values each
action for the deep Q-network and PQN, and `ActorCritic`, which PPO trains,
beside `Encoder`, which both read each observation through, `ChannelNorm`,
`acting_network` and `seeded_network`, which build the one an agent acts
through, and `tensors`, which moves a batch of observations onto a device.
"""

from collections.abc  import Mapping
from gymnasium.spaces import Dict, flatten_space
from numpy            import ndarray
from torch            import Tensor, as_tensor, cat, default_generator, set_num_threads, uint8, zeros
from torch.backends   import nnpack
from torch.nn         import Conv2d, Flatten, Identity, LayerNorm, LazyConv2d, LazyLinear, Linear, Module, ModuleDict
from torch.nn         import ReLU, Sequential
from torch.random     import fork_rng

from squirtl.agent.schemas import AgentSettings, Algorithm


class ActorCritic(Module):
    """
    The network PPO trains, whose `Encoder` reads each observation through
    two fully connected layers, the projection of the encodings and the body
    Pleines et al. describe, before a head of the policy's logits and a head
    of the value, sharing every layer beneath them as theirs does.
    """

    def __init__(self, actions: int, space: Dict):
        """
        Builds the encoder over `space` and both heads, the policy's over
        `actions` actions.
        """
        super().__init__()

        self.critic  = Linear(512, 1)
        self.encoder = Encoder(space, depth=2, normalized=False)
        self.policy  = Linear(512, actions)

    def forward(self, observations: Mapping[str, Tensor]) -> Tensor:
        """
        Reads the policy's logits over the actions for each observation,
        whose largest names the most likely action.
        """
        return self.policy(self.encoder(observations))

    def heads(self, observations: Mapping[str, Tensor]) -> tuple[Tensor, Tensor]:
        """
        Reads the policy's logits and the value for each observation from
        one pass through the encoder.

        Returns:
            A `(batch, actions)` tensor of logits beside a `(batch,)` tensor
            of values.
        """
        features = self.encoder(observations)

        return self.policy(features), self.critic(features)[:, 0]


class ChannelNorm(LayerNorm):
    """
    Layer normalization over each position's channels of a `(batch,
    channels, height, width)` tensor, as Flax's `LayerNorm` normalizes the
    last axis of the channels-last tensors Gallici et al.'s Atari network
    reads.
    """

    def forward(self, images: Tensor) -> Tensor:
        """
        Normalizes `images` with its channels moved last, then moves them
        back.
        """
        return super().forward(images.movedim(1, -1)).movedim(-1, 1)


class Encoder(Module):
    """
    The layers every agent's network reads an observation through, which
    read each entry of a `Dict` observation through its own encoder and
    concatenate the encodings before `depth` fully connected layers of 512
    units, as Pleines et al. do, with Mnih et al.'s convolutions and no
    batch normalization. Each entry stacks along its first axis, so at the
    default settings an observation holds a `(4, 72, 80)` stack of frames,
    a `(1, 48, 48)` grid, and a `(1, 4)` vector of flags. Where `normalized`
    is set, layer normalization runs over each position's channels after
    every convolution and over each fully connected layer before its
    activation, as Gallici et al.'s Atari network normalizes.
    """

    def __init__(self, space: Dict, *, depth: int, normalized: bool):
        """
        Builds an encoder per entry `space` declares and the fully connected
        layers, then runs an observation of zeros through them, which sets
        each lazy layer's depth and width.
        """
        super().__init__()

        channels, features = (
            ChannelNorm, LayerNorm
        ) if normalized else (Identity, Identity)

        self.encoders = ModuleDict(
            {
                key: self.encoder(channels, features, entry.shape)
                for key, entry in space.items()
            }
        )
        self.highs = {
            key: float(flatten_space(entry).high.max()) for key, entry in space.items()
        }
        self.layers = Sequential(
            LazyLinear(512),
            features(512),
            ReLU(),
            *(
                module
                for _ in range(depth - 1)
                for module in (Linear(512, 512), features(512), ReLU())
            )
        )

        self({key: zeros(1, *entry.shape, dtype=uint8) for key, entry in space.items()})

    @staticmethod
    def encoder(
        channels : type[Module],
        features : type[Module],
        shape    : tuple[int, ...]
    ) -> Sequential:
        """
        Builds Mnih et al.'s three convolutions for a stack of images, its
        depth read as channels, each followed by `channels` over its own
        width. For a stack of vectors, it builds one fully connected layer
        of 64 units, the width Pleines et al.'s published configuration
        gives, followed by `features` over that width.

        Raises:
            ValueError: Where `shape` is neither stack.
        """
        match shape:
            case (_, _, _):
                return Sequential(
                    LazyConv2d(32, 8, stride=4),
                    channels(32),
                    ReLU(),
                    Conv2d(32, 64, 4, stride=2),
                    channels(64),
                    ReLU(),
                    Conv2d(64, 64, 3),
                    channels(64),
                    ReLU(),
                    Flatten()
                )
            case (_, _):
                return Sequential(Flatten(), LazyLinear(64), features(64), ReLU())
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

        Returns:
            The last layer's 512 features for each observation.
        """
        return self.layers(
            cat(
                [
                    encoder(observations[key] / self.highs[key])
                    for key, encoder in self.encoders.items()
                ],
                1
            )
        )


class QNetwork(Module):
    """
    The Q-network the deep Q-network and PQN train, whose `Encoder` reads
    each observation through one fully connected layer before Mnih et al.'s
    head of one value per action, each layer beneath the head normalized
    for PQN.
    """

    def __init__(self, actions: int, space: Dict, normalized: bool = False):
        """
        Builds the encoder over `space`, normalizing each of its layers
        where `normalized` is set, and the head over `actions` actions.
        """
        super().__init__()

        self.encoder = Encoder(space, depth=1, normalized=normalized)
        self.head    = Linear(512, actions)

    def forward(self, observations: Mapping[str, Tensor]) -> Tensor:
        """
        Values each action for each observation.
        """
        return self.head(self.encoder(observations))


def acting_network(actions: int, algorithm: Algorithm, space: Dict) -> Module:
    """
    Builds the network `algorithm` acts through for `actions` actions
    over `space`, a `QNetwork` for the deep Q-network, one whose encoder
    normalizes each layer for PQN, and an `ActorCritic` for PPO.
    """
    match algorithm:
        case Algorithm.DQN : return QNetwork(actions, space)
        case Algorithm.PPO : return ActorCritic(actions, space)
        case Algorithm.PQN : return QNetwork(actions, space, normalized=True)


def seeded_network(
    actions  : int,
    seed     : int,
    settings : AgentSettings,
    space    : Dict
) -> Module:
    """
    Builds the network `settings` names on its device, under a fork of
    PyTorch's global generator seeded from `seed`. It first turns NNPACK off
    for the whole process, which runs these networks' convolutions on the
    CPU slower than PyTorch's own, and sets the process's thread count to
    `threads`, where the settings name one.
    """
    nnpack.set_flags(False)

    if settings.threads:
        set_num_threads(settings.threads)

    with fork_rng(devices=[]):
        default_generator.manual_seed(seed)

        return acting_network(actions, settings.algorithm, space).to(settings.device)


def tensors(device: str, observations: Mapping[str, ndarray]) -> dict[str, Tensor]:
    """
    Moves each entry of `observations` onto `device`.
    """
    return {key: as_tensor(entry, device=device) for key, entry in observations.items()}
