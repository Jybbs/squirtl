"""
Pins the Q-network, covering the layers it carries, the values it maps a
batch of `uint8` observations to, the scaling it applies to each entry, the
absence of any layer whose output depends on the batch or the mode, and the
entry it refuses.
"""

from gymnasium.spaces import Box, Dict
from pytest           import mark, param, raises
from re               import escape
from syrupy.assertion import SnapshotAssertion
from torch            import Tensor, cat, equal, manual_seed, randint, uint8
from torch.testing    import assert_close

from squirtl.agent.networks import QNetwork


def draw(batch: int, space: Dict) -> dict[str, Tensor]:
    """
    Draws `batch` random observations of `space`, each entry within the
    bound its space declares.
    """
    return {
        key: randint(int(entry.high.max()) + 1, (batch, *entry.shape), dtype=uint8)
        for key, entry in space.items()
    }


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
    Asserts that the network maps a batch of observations whose frames
    take any size its convolutions reach to one value per action for each
    observation, the first linear layer of its head reading whatever width
    the encoders leave.
    """
    resized = Dict(dict(space) | {"frames": Box(0, 255, frames, space["frames"].dtype)})
    manual_seed(0)

    assert QNetwork(7, resized)(draw(3, resized)).shape == (3, 7)


def test_the_network_carries_the_layers_mnih_et_al_set(
    snapshot : SnapshotAssertion,
    space    : Dict
):
    """
    Asserts that the network for seven actions over the observation the
    environment makes carries its own copy of the three convolutions Mnih
    et al. set for the frames and for the grid, one fully connected layer of
    64 units for the flags, and the two linear layers Mnih et al. set as its
    head, with no batch normalization, so a change to any layer is reviewed
    as a diff.
    """
    assert str(QNetwork(7, space)) == snapshot


def test_the_network_scales_each_entry_into_the_unit_interval(space: Dict):
    """
    Asserts that the network divides each entry by the bound its space
    declares before that entry's encoder reads it, the frames by 255 and the
    grid and the flags by 1.
    """
    manual_seed(0)
    network      = QNetwork(7, space)
    observations = draw(2, space)

    assert equal(
        network(observations),
        network.head(
            cat(
                [
                    network.encoders["flags"](observations["flags"].float()),
                    network.encoders["frames"](observations["frames"] / 255),
                    network.encoders["grid"](observations["grid"].float())
                ],
                1
            )
        )
    )


def test_the_network_values_an_observation_alike_in_training_and_in_evaluation(
    space: Dict
):
    """
    Asserts that the network values an observation the same in training
    mode as in evaluation mode and the same alone as inside a batch, which a
    batch normalization layer's running statistics would break.
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
