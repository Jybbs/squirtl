"""
Pins the Q-network, covering the layers it carries, the values it maps a
batch of stacked `uint8` frames to, the scaling it applies to them, and the
absence of any layer whose output depends on the batch or the mode.
"""

from pytest           import mark, param
from syrupy.assertion import SnapshotAssertion
from torch            import equal, manual_seed, randint, uint8
from torch.nn         import Sequential
from torch.testing    import assert_close

from squirtl.agent.networks import QNetwork


@mark.parametrize(
    "shape",
    [
        param((4, 72, 80), id="four-72-by-80-frames"),
        param((4, 36, 36), id="four-36-by-36-frames")
    ]
)
def test_the_network_maps_each_stack_to_one_value_per_action(shape: tuple[int, ...]):
    """
    Asserts that the network maps a batch of stacks of any frame size its
    convolutions reach to one value per action for each stack, the first
    linear layer reading whatever width the convolutions leave.
    """
    manual_seed(0)

    assert QNetwork(7, shape)(randint(256, (3, *shape), dtype=uint8)).shape == (3, 7)


def test_the_network_carries_the_layers_mnih_et_al_set(snapshot: SnapshotAssertion):
    """
    Asserts that the network for seven actions over four stacked 72 by 80
    frames carries the three convolutions and two linear layers Mnih et al.
    set, with no batch normalization, so a change to any layer is reviewed
    as a diff.
    """
    assert str(QNetwork(7, (4, 72, 80))) == snapshot


def test_the_network_scales_each_frame_into_the_unit_interval():
    """
    Asserts that the network reads a stack of `uint8` frames as the layers
    read that stack divided by 255.
    """
    manual_seed(0)
    network      = QNetwork(7, (4, 72, 80))
    observations = randint(256, (2, 4, 72, 80), dtype=uint8)

    assert equal(network(observations), Sequential.forward(network, observations / 255))


def test_the_network_values_a_stack_alike_in_training_and_in_evaluation():
    """
    Asserts that the network values a stack the same in training mode as
    in evaluation mode and the same alone as inside a batch, which a batch
    normalization layer's running statistics would break.
    """
    manual_seed(0)
    network      = QNetwork(7, (4, 72, 80))
    observations = randint(256, (5, 4, 72, 80), dtype=uint8)
    trained      = network.train()(observations)

    assert equal(network.eval()(observations), trained)
    assert_close(network(observations[:1]), trained[:1])
