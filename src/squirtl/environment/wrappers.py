"""
Defines `ProgressObservation` and `ShrinkObservation`, the observation
wrappers `Overworld.make` applies beside Gymnasium's own.
"""

from gymnasium        import Env, ObservationWrapper
from gymnasium.spaces import Box, Dict, MultiBinary
from gymnasium.utils  import RecordConstructorArgs
from numpy            import ndarray, uint8

from squirtl.environment.schemas import Entry
from squirtl.reward.schemas      import Event


class ProgressObservation(ObservationWrapper, RecordConstructorArgs):
    """
    Observes beside the stacked frames the progress the reward reads, as
    Pleines et al. observe, each entry stacked along its first axis:

    - `FLAGS`, one deep, from `Progress.flags`
    - `FRAMES`, the stack the wrapped environment observes
    - `GRID`, one deep, from `Progress.grid`, marking each position reached
    """

    def __init__(self, env: Env, size: int):
        """
        Wraps `env`, whose observation is the frame stack, with a grid
        `size` squares a side.
        """
        RecordConstructorArgs.__init__(self, size=size)
        ObservationWrapper.__init__(self, env)

        self.observation_space = Dict(
            {
                Entry.FLAGS  : MultiBinary((1, len(Event))),
                Entry.FRAMES : env.observation_space,
                Entry.GRID   : MultiBinary((1, size, size))
            }
        )
        self.size = size

    def observation(self, observation: ndarray) -> dict[Entry, ndarray]:
        """
        Sets the frame stack beside the flags and the grid of the unwrapped
        environment's `Progress`, read once the step or the reset has run.
        """
        progress = self.get_wrapper_attr("progress")

        return {
            Entry.FLAGS  : progress.flags[None],
            Entry.FRAMES : observation,
            Entry.GRID   : progress.grid(self.size)[None]
        }


class ShrinkObservation(ObservationWrapper, RecordConstructorArgs):
    """
    Shrinks each grayscale frame to `shape` by averaging the block of pixels
    each cell covers, in integers rounding a half up.
    """

    def __init__(self, env: Env, shape: tuple[int, int]):
        """
        Wraps `env`, whose grayscale frame each side of `shape` divides.
        """
        RecordConstructorArgs.__init__(self, shape=shape)
        ObservationWrapper.__init__(self, env)

        self.observation_space = Box(0, 255, shape, uint8)
        self.shape             = shape

    def observation(self, frame: ndarray) -> ndarray:
        """
        Averages each block of `frame` into its cell of `shape`.

        Returns:
            A `shape` array of `uint8`.
        """
        height, width = self.shape
        blocks        = frame.reshape(
            height,
            frame.shape[0] // height,
            width,
            frame.shape[1] // width
        )
        cells = blocks.shape[1] * blocks.shape[3]

        return ((blocks.sum(axis=(1, 3)) + cells // 2) // cells).astype(uint8)
