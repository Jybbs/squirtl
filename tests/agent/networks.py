"""
Pins the networks the agents train, covering:

- The Q-network's layers, the values it maps observations to, the scaling of
  each entry, its sameness across batches and modes, and the entry it refuses
- The layers PQN's Q-network normalizes and PPO's network adds, and what
  `ChannelNorm` normalizes over
- The logits and the values PPO's network reads from one pass of its encoder
- `tensors` moving each entry onto the device it names
- The network each agent builds, PQN's alone normalized
"""

from collections.abc        import Callable
from gymnasium.spaces       import Box, Dict
from gymnasium.vector.utils import batch_space
from numpy            import ones, uint8
from pytest           import mark, param, raises
from re               import escape
from syrupy.assertion import SnapshotAssertion
from torch            import Tensor, arange, as_tensor, cat, equal, manual_seed, zeros
from torch.nn         import LayerNorm, Module
from torch.testing    import assert_close

from squirtl.agent.networks      import ActorCritic, ChannelNorm, QNetwork, acting_network, tensors
from squirtl.agent.schemas       import Algorithm
from squirtl.environment.schemas import Entry


def draw(batch: int, space: Dict) -> dict[str, Tensor]:
    """
    Draws `batch` random observations of `space` from seed 0.
    """
    batched = batch_space(space, batch)
    batched.seed(0)

    return {key: as_tensor(entry) for key, entry in batched.sample().items()}


@mark.parametrize(
    "frames",
    [
        param((4, 72, 80), id="four-72-by-80-frames"),
        param((4, 36, 36), id="four-36-by-36-frames")
    ]
)
def test_the_network_maps_each_observation_to_one_value_per_action(
    frames : tuple[int, ...],
    space  : Dict
):
    """
    Asserts that the network maps observations whose frames take any
    size its convolutions reach to one value per action, its head reading
    whatever width the encoders leave.
    """
    resized = Dict(
        dict(space) | {Entry.FRAMES: Box(0, 255, frames, space[Entry.FRAMES].dtype)}
    )
    manual_seed(0)

    assert QNetwork(7, resized)(draw(3, resized)).shape == (3, 7)


def test_a_channel_norm_normalizes_each_position_over_its_channels():
    """
    Asserts that `ChannelNorm` keeps the shape of a batch of images and
    leaves each position's channels at a mean of 0 and a variance of 1,
    whatever the scale of the channels at any other position, which a norm
    over the image would not.
    """
    images = cat(
        [
            arange(1.0, 13.0).reshape(1, 3, 2, 2),
            1000 * arange(1.0, 13.0).reshape(1, 3, 2, 2)
        ],
        3
    )
    normed = ChannelNorm(3)(images)

    assert normed.shape == images.shape
    assert_close(normed.mean(1), zeros(1, 2, 4), atol=1e-5, rtol=0)
    assert_close(normed.var(1, unbiased=False), zeros(1, 2, 4) + 1, atol=1e-3, rtol=0)


@mark.parametrize(
    "network",
    [
        param(lambda space: QNetwork(7, space, normalized=True), id="pqn"),
        param(lambda space: ActorCritic(7, space),               id="ppo")
    ]
)
def test_each_agents_network_carries_the_layers_its_source_sets(
    network  : Callable[[Dict], Module],
    snapshot : SnapshotAssertion,
    space    : Dict
):
    """
    Asserts that PQN's network normalizes each position's channels after
    every convolution and each fully connected layer before its activation,
    as Gallici et al.'s Atari network does, and that PPO's normalizes
    nothing and projects the encodings before a body of 512 units and its
    two heads, as Pleines et al. describe.
    """
    assert str(network(space)) == snapshot


def test_a_normalized_network_values_an_observation_alike_alone_or_batched(space: Dict):
    """
    Asserts that layer normalization leaves PQN's network valuing an
    observation alike alone and in a batch, since it reads no other
    observation of the batch.
    """
    manual_seed(0)
    network      = QNetwork(7, space, normalized=True)
    observations = draw(5, space)

    assert_close(
        network({key: entry[:1] for key, entry in observations.items()}),
        network(observations)[:1]
    )


def test_ppos_network_reads_its_logits_and_its_values_from_one_pass(space: Dict):
    """
    Asserts that PPO's network reads a `(batch, actions)` tensor of logits
    and a `(batch,)` tensor of values for a batch of three, its forward pass
    returning the same logits, with both heads reading one encoder.
    """
    manual_seed(0)
    network        = ActorCritic(7, space)
    observations   = draw(3, space)
    logits, values = network.heads(observations)

    assert (logits.shape, values.shape) == ((3, 7), (3,))
    assert equal(network(observations), logits)
    assert equal(values, network.critic(network.encoder(observations))[:, 0])


def test_tensors_moves_each_entry_onto_the_device_it_names():
    """
    Asserts that `tensors` moves each entry onto the device it names,
    keeping its shape, which the `meta` device pins on a machine with no
    accelerator.
    """
    moved = tensors("meta", {"flags": ones(4, uint8), "frames": ones((2, 3), uint8)})

    assert {entry.device.type for entry in moved.values()} == {"meta"}
    assert moved["frames"].shape == (2, 3)


def test_the_network_carries_the_layers_mnih_et_al_set(
    snapshot : SnapshotAssertion,
    space    : Dict
):
    """
    Asserts that the network carries Mnih et al.'s convolutions for the
    frames and the grid each, 64 fully connected units for the flags, and
    Mnih et al.'s head, with no batch normalization.
    """
    assert str(QNetwork(7, space)) == snapshot


def test_the_network_scales_each_entry_into_the_unit_interval(space: Dict):
    """
    Asserts that the network divides each entry by its space's bound before
    its encoder reads it, the frames by 255 and the grid and the flags by 1.
    """
    manual_seed(0)
    network      = QNetwork(7, space)
    observations = draw(2, space)

    encoders = network.encoder.encoders

    assert equal(
        network(observations),
        network.head(
            network.encoder.layers(
                cat(
                    [
                        encoders[Entry.FLAGS](observations[Entry.FLAGS].float()),
                        encoders[Entry.FRAMES](observations[Entry.FRAMES] / 255),
                        encoders[Entry.GRID](observations[Entry.GRID].float())
                    ],
                    1
                )
            )
        )
    )


def test_the_network_values_an_observation_alike_in_training_and_in_evaluation(
    space: Dict
):
    """
    Asserts that the network values an observation alike in training and in
    evaluation mode and alone or batched, which batch normalization would
    break.
    """
    manual_seed(0)
    network      = QNetwork(7, space)
    observations = draw(5, space)
    trained      = network.train()(observations)

    assert equal(network.eval()(observations), trained)
    assert_close(
        network({key: entry[:1] for key, entry in observations.items()}),
        trained[:1]
    )


@mark.parametrize(
    "shape",
    [param((4,), id="a-vector"), param((1, 4, 72, 80), id="a-stack-of-stacks")]
)
def test_the_network_refuses_an_entry_neither_images_nor_vectors(
    shape: tuple[int, ...]
):
    """
    Asserts that the network refuses an entry whose shape is neither a stack
    of images nor a stack of vectors, naming that shape.
    """
    with raises(ValueError, match=escape(f"shape {shape} ")):
        QNetwork(7, Dict(entry=Box(0, 1, shape)))


@mark.parametrize(
    ("algorithm", "network", "normalized"),
    [
        param(Algorithm.DQN, QNetwork,    False, id="the-deep-q-network"),
        param(Algorithm.PPO, ActorCritic, False, id="ppo"),
        param(Algorithm.PQN, QNetwork,    True,  id="pqn")
    ]
)
def test_each_agent_builds_the_network_it_acts_through(
    algorithm  : Algorithm,
    network    : type[Module],
    normalized : bool
):
    """
    Asserts that each agent builds its own network over seven actions, PQN's
    alone normalized.
    """
    built = acting_network(7, algorithm, Dict(frames=Box(0, 255, (4, 72, 80))))

    assert type(built) is network
    assert any(isinstance(layer, LayerNorm) for layer in built.modules()) is normalized
