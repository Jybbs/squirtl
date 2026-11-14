"""
Pins the random network distillation scoring a search's frame
stacks, covering:

- The networks of Appendix A.3, built from a seed on the convolutions the
  Q-network builds, with the initialization Burda et al. release, and the
  global generator left undrawn
- The inputs normalized by the running mean and deviation and clipped, and
  each convolution and its inputs in the `channels_last` memory format
- The frames stored in replay memory, capped at its capacity, with each stack
  rebuilt from the frames before it, and a rollout's stack stored only where
  replay memory does not already end on it, each rollout waiting on updates
  stored after the one it continues
- The updates owed for the presses taken, which train the predictor and
  leave the target alone, and the score falling on what it has seen
- The updates running on a thread of their own, which the scores and the
  frames observed meanwhile leave as they would run alone
- The arrays and the networks loading back into a search, and a network of
  another shape refused
"""

from collections.abc  import Iterator
from common.search    import snapshot
from contextlib       import contextmanager
from copy             import deepcopy
from gymnasium.spaces import Box
from gymnasium.wrappers.utils import RunningMeanStd
from numpy         import array_equal, full, identity, uint8
from numpy.random  import default_rng
from pytest        import MonkeyPatch, approx, raises
from threading     import Event
from torch         import Tensor, as_tensor, channels_last, get_rng_state, manual_seed, ones, zeros
from torch.nn      import Conv2d, Linear
from torch.testing import assert_close

from squirtl.agent.schemas  import AgentSettings
from squirtl.search.novelty import Novelty
from squirtl.search.schemas import SearchSettings

FRAME = 72 * 80


def build(settings: SearchSettings, space: Box, seed: int = 7) -> Novelty:
    """
    Builds the predictor of `settings` over `space` from `seed` on the CPU.
    """
    return Novelty(
        AgentSettings(device="cpu"),
        default_rng(seed),
        seed,
        settings,
        space
    )


def centered(level: int, novelty: Novelty) -> Tensor:
    """
    Scores the stack of pixels at `level` on a running mean of `level`.

    Returns:
        The error of the stack's prediction.
    """
    novelty.normalizer.mean = full((72, 80), float(level))

    return errors(as_tensor(full((1, 4, 72, 80), level, uint8)), novelty)


def errors(frames: Tensor, novelty: Novelty) -> Tensor:
    """
    Measures the predictor's error on `frames` under the running statistics.
    """
    return novelty.error(frames, novelty.normalizer, novelty.predictor)


@contextmanager
def held(monkeypatch: MonkeyPatch, novelty: Novelty) -> Iterator[Event]:
    """
    Holds each update of `novelty` once it has stepped the predictor, until
    the block ends, releasing them however the block exits, since a thread
    held past a failing assertion leaves pytest joining it at exit.

    Yields:
        The event set once the first update has stepped.
    """
    stepped, released = Event(), Event()
    update            = novelty.update

    def holding(normalizer: RunningMeanStd) -> float:
        """
        Takes one update, then holds until the block ends.
        """
        loss = update(normalizer)  # prose: ignore[inlinable-bindings]

        stepped.set()
        released.wait()

        return loss

    monkeypatch.setattr(novelty, "update", holding)

    try:
        yield stepped
    finally:
        released.set()


def seen(novelty: Novelty, *shades: int, start: int = 0):
    """
    Stores a rollout of one frame of each of `shades` from a stack of frames
    of `start`.
    """
    novelty.observe(
        b"".join(bytes([shade]) * FRAME for shade in shades),
        snapshot(shade=start)
    )


def stored(novelty: Novelty) -> list[int]:
    """
    Reads the shade of each frame replay memory holds, slot by slot.
    """
    return novelty.replay.arrays["frames"][:, 0, 0].tolist()


def test_a_continuing_rollout_leaves_older_frames_in_replay_memory(
    small : SearchSettings,
    space : Box
):
    """
    Asserts that at a capacity of 8, a rollout of 3 presses continuing one
    of 6 leaves that rollout's second frame in replay memory, which storing
    the continuing rollout's stack again would overwrite, and that every
    transition between the frames held stays drawable.
    """
    novelty = build(small.model_copy(update={"capacity": 8}), space)

    seen(novelty, 1, 2, 5, 5, 5, 5)
    seen(novelty, 6, 7, 8, start=5)

    assert sorted(stored(novelty)) == [2, 5, 5, 5, 5, 6, 7, 8]
    assert novelty.replay.held.sum() == 4


def test_a_network_of_another_shape_is_refused(novelty: Novelty, small: SearchSettings):
    """
    Asserts that loading the networks of another frame shape raises, naming
    what differs.
    """
    other = build(small, Box(0, 255, (4, 36, 40), uint8))

    with raises(ValueError, match="networks differ"):
        novelty.load(novelty.arrays, other.networks)


def test_a_rollout_continuing_the_last_one_stored_stores_its_frames_alone(
    novelty: Novelty
):
    """
    Asserts that a rollout starting from the stack replay memory ends on
    stores its frames alone, while one starting elsewhere stores its stack
    before them.
    """
    seen(novelty, 5, 5, 5, 5)
    seen(novelty, 6, 7, start=5)
    seen(novelty, 3, start=0)

    assert stored(novelty)[:15] == [0, 0, 0, 0, 5, 5, 5, 5, 6, 7, 0, 0, 0, 0, 3]
    assert novelty.replay.arrays["pushed"].item() == 15


def test_a_score_reads_each_snapshots_stack_in_order(novelty: Novelty):
    """
    Asserts that a score holds one value per snapshot, in their order,
    equal for equal stacks, once the running statistics hold the frames that
    normalize them.
    """
    seen(novelty, 10, 20, 30)

    first, second, third = novelty.score(
        snapshot(shade=shade) for shade in (5, 90, 5)
    )

    assert first == third != second


def test_a_seed_fixes_both_networks(small: SearchSettings, space: Box):
    """
    Asserts that one seed builds the same two networks, and that the two
    differ from each other.
    """
    manual_seed(0)

    first  = build(small, space)
    second = build(small, space)

    assert_close(first.target.state_dict(), second.target.state_dict(), atol=0, rtol=0)
    assert_close(
        first.predictor.state_dict(),
        second.predictor.state_dict(),
        atol = 0,
        rtol = 0
    )
    assert (
        first.predictor(ones(1, 4, 72, 80))
             .ne(first.target(ones(1, 4, 72, 80)))
             .any()
    )


def test_a_seed_of_another_value_builds_other_networks(
    small : SearchSettings,
    space : Box
):
    """
    Asserts that another seed builds another target.
    """
    first, second = (build(small, space, seed).target[-1].weight for seed in (7, 8))

    assert first.ne(second).any()


def test_an_update_steps_the_predictor_and_leaves_the_target_alone(novelty: Novelty):
    """
    Asserts that an update changes the predictor's weights and leaves the
    target's as they were.
    """
    predictor, target = (
        network[-1].weight.clone() for network in (novelty.predictor, novelty.target)
    )

    seen(novelty, *range(20))
    novelty.update(novelty.normalizer)

    assert novelty.predictor[-1].weight.ne(predictor).any()
    assert_close(novelty.target[-1].weight, target, atol=0, rtol=0)


def test_building_the_networks_draws_nothing_from_the_global_generator(
    small : SearchSettings,
    space : Box
):
    """
    Asserts that the global generator holds the state it held as each
    predictor is built.
    """
    before = get_rng_state()

    for _ in range(2):
        build(small, space)

        assert_close(get_rng_state(), before, atol=0, rtol=0)


def test_each_network_builds_the_appendixs_head_on_the_q_networks_convolutions(
    novelty: Novelty
):
    """
    Asserts that each network's head is two linear layers of 1024 units
    separated by a ReLU, reading the flattened convolutions.
    """
    linear = [
        module for module in novelty.predictor.modules() if isinstance(module, Linear)
    ]

    assert [layer.out_features for layer in linear] == [1024, 1024]
    assert novelty.predictor(zeros(1, 4, 72, 80)).shape == (1, 1024)


def test_observing_adds_each_frame_to_the_running_statistics(novelty: Novelty):
    """
    Asserts that the running mean of a rollout's frames follows each frame,
    and leaves out the start's stack, which an earlier rollout observed.
    """
    seen(novelty, 10, 20, 30)

    assert novelty.normalizer.mean == approx(full((72, 80), 20.0), rel=1e-3)
    assert novelty.normalizer.count == approx(3, rel=1e-3)


def test_observing_past_the_capacity_keeps_the_newest_frames(
    small : SearchSettings,
    space : Box
):
    """
    Asserts that storing past the capacity keeps its slot count, overwriting
    the oldest frame.
    """
    novelty = build(small.model_copy(update={"capacity": 8}), space)

    seen(novelty, *range(1, 11))

    assert novelty.replay.arrays["pushed"].item() == 14
    assert novelty.replay.arrays["frames"].shape[0] == 8


def test_observing_stores_the_stack_and_each_frame_after_it(novelty: Novelty):
    """
    Asserts that a rollout of three presses stores the four frames of its
    start beside its three newest frames, and that a stack drawn rebuilds
    from those frames, the newest last.
    """
    seen(novelty, 10, 20, 30)

    assert novelty.replay.arrays["pushed"].item() == 7

    for stack in novelty.replay.sample("cpu", 4).next_observations["frames"].numpy():
        assert stack[-1, 0, 0] in (10, 20, 30)


def test_rollouts_observed_while_updates_run_follow_the_ones_they_continue(
    novelty: Novelty
):
    """
    Asserts that rollouts observed while updates run reach replay memory
    once they are waited for, each after the rollout whose newest stack it
    starts from and the rest in the order they were observed, so a stack
    continuing another is stored once.
    """
    novelty.train(0)

    seen(novelty, 5, 5, 5, 5)
    seen(novelty, 3)
    seen(novelty, 6, 7, start=5)
    novelty.wait()

    assert stored(novelty)[:15] == [0, 0, 0, 0, 5, 5, 5, 5, 6, 7, 0, 0, 0, 0, 3]


def test_the_arrays_and_networks_load_back_as_a_search_continues_from_them(
    novelty : Novelty,
    small   : SearchSettings,
    space   : Box
):
    """
    Asserts that a predictor loading what another gathered, built from
    another seed, then draws the same batches and takes the same updates.
    """
    seen(novelty, *range(1, 21))
    novelty.update(novelty.normalizer)

    loaded = build(small, space, seed=9)
    loaded.load(novelty.arrays, deepcopy(novelty.networks))

    assert loaded.updates == novelty.updates
    assert loaded.update(loaded.normalizer) == novelty.update(novelty.normalizer)
    assert_close(
        loaded.predictor.state_dict(),
        novelty.predictor.state_dict(),
        atol = 0,
        rtol = 0
    )
    assert array_equal(loaded.normalizer.mean, novelty.normalizer.mean)


def test_the_convolutions_and_their_inputs_take_the_channels_last_format(
    novelty: Novelty
):
    """
    Asserts that every convolution of both networks holds its weights
    in the `channels_last` memory format, and that the error on a stack
    equals the error both networks give the same normalized stack laid out
    contiguously, so the format changes the layout and not the result.
    """
    stack  = as_tensor(default_rng(3).integers(0, 256, (2, 4, 72, 80), uint8))
    inputs = (stack.float() - as_tensor(novelty.normalizer.mean).float()).clamp(-5, 5)

    assert all(
        module.weight.is_contiguous(memory_format=channels_last)
        for network in (novelty.predictor, novelty.target)
        for module in network.modules()
        if isinstance(module, Conv2d)
    )
    assert_close(
        errors(stack, novelty),
        (novelty.predictor(inputs) - novelty.target(inputs)).square().mean(1),
        atol = 1e-6,
        rtol = 1e-5
    )


def test_the_convolutions_take_orthogonal_weights_at_a_gain_of_root_2_and_no_bias(
    novelty: Novelty
):
    """
    Asserts that each convolution's filters, flattened, are orthogonal with
    squared norm 2, which an orthogonal matrix at a gain of the square root
    of 2 holds, and that each bias is zero.
    """
    for module in novelty.target[0]:
        if isinstance(module, Conv2d):
            rows = (
                module.weight.detach()
                      .flatten(1)
                      .numpy()
            )
            gram = rows @ rows.T if rows.shape[0] <= rows.shape[1] else rows.T @ rows

            assert gram == approx(2 * identity(min(rows.shape)), abs=1e-5)
            assert not module.bias.any()


def test_the_inputs_clip_to_five_deviations_of_the_running_statistics(novelty: Novelty):
    """
    Asserts that a stack lying far past five deviations of the running mean
    scores as the stack lying exactly five past it, each pixel clipped to
    the bound.
    """
    novelty.normalizer.mean = full((72, 80), 100.0)
    novelty.normalizer.var  = full((72, 80), 4.0)

    frames    = (full((1, 4, 72, 80), value, uint8) for value in (110, 200))
    near, far = (errors(as_tensor(stack), novelty) for stack in frames)

    assert_close(near, far, atol=0, rtol=0)


def test_the_inputs_divide_by_the_running_deviation(novelty: Novelty):
    """
    Asserts that a stack at the running mean scores as a stack of zeros
    on statistics of mean zero, whatever the deviation, since each pixel
    normalizes to zero.
    """
    novelty.normalizer.var = full((72, 80), 9.0)

    assert_close(centered(100, novelty), centered(0, novelty), atol=0, rtol=0)


def test_the_score_of_a_stack_falls_as_the_predictor_trains_on_it(novelty: Novelty):
    """
    Asserts that repeating one stack through replay memory lowers its score,
    which is what ranks an unseen stack above a familiar one.
    """
    seen(novelty, *[40] * 32)

    assert trained(novelty, 0) > trained(novelty, 32)


def test_the_target_requires_no_gradient(novelty: Novelty):
    """
    Asserts that no parameter of the target takes a gradient, whereas every
    one of the predictor's does.
    """
    assert not any(parameter.requires_grad for parameter in novelty.target.parameters())
    assert all(parameter.requires_grad for parameter in novelty.predictor.parameters())


def test_training_takes_the_updates_the_presses_owe(novelty: Novelty):
    """
    Asserts that training after 20 presses at one update every 8 takes two,
    that training at those presses again takes none and returns `None`, and
    that it counts on from there, while waiting with nothing started returns
    `None`.
    """
    seen(novelty, *range(20))

    assert novelty.wait() is None

    novelty.train(20)

    assert (novelty.wait() > 0.0, novelty.updates) == (True, 2)

    novelty.train(20)

    assert novelty.wait() is None

    novelty.train(24)

    assert (novelty.wait() is not None, novelty.updates) == (True, 3)


def test_updates_running_alongside_a_search_take_what_they_would_alone(
    monkeypatch : MonkeyPatch,
    small       : SearchSettings,
    space       : Box
):
    """
    Asserts that updates observing a rollout and scoring while they run, the
    first update held once it has stepped, reach the weights and the loss
    of the same updates run with nothing beside them, since each draws only
    from what replay memory held and normalizes by the running statistics as
    they stood when the updates started.
    """
    alone, beside = build(small, space), build(small, space)

    for novelty in (alone, beside):
        seen(novelty, *range(1, 41))

    alone.train(40)

    with held(monkeypatch, beside) as stepped:
        beside.train(40)
        stepped.wait()
        seen(beside, *range(100, 140))
        beside.score([snapshot(shade=60)])

    assert beside.wait() == alone.wait()
    assert_close(
        beside.predictor.state_dict(),
        alone.predictor.state_dict(),
        atol = 0,
        rtol = 0
    )


def test_while_updates_run_a_score_reads_the_predictor_from_their_start(
    monkeypatch : MonkeyPatch,
    novelty     : Novelty
):
    """
    Asserts that a score taken once the first update has stepped the
    predictor, the rest held back, equals one taken before the updates
    started, and that once they are waited for, a score reads the updated
    predictor.
    """
    seen(novelty, *[40] * 32)

    before = novelty.score([snapshot(shade=40)])

    with held(monkeypatch, novelty) as stepped:
        novelty.train(32)
        stepped.wait()

        assert novelty.score([snapshot(shade=40)]) == before

    novelty.wait()

    assert novelty.score([snapshot(shade=40)]) != before


def test_while_updates_run_the_frames_observed_wait_outside_replay_memory(
    novelty: Novelty
):
    """
    Asserts that a rollout observed while updates run adds its frames to
    the running statistics at once and reaches replay memory only once the
    updates are waited for, after what it held before.
    """
    seen(novelty, 10, 20, 30)
    novelty.train(0)
    seen(novelty, 50, 60, 70)

    assert novelty.replay.arrays["pushed"].item() == 7
    assert novelty.normalizer.count == approx(6, rel=1e-3)

    novelty.wait()

    assert novelty.replay.arrays["pushed"].item() == 14


def trained(novelty: Novelty, updates: int) -> float:
    """
    Takes `updates` updates of the predictor.

    Returns:
        The score of a stack of pixels at 40.
    """
    for _ in range(updates):
        novelty.update(novelty.normalizer)

    return novelty.score([snapshot(shade=40)])[0]
