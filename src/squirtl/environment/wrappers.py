"""
Defines `ProgressObservation`, the observation wrapper that sets beside the
stacked frames what the reward reads, which `Overworld.make` applies after
Gymnasium's own observation wrappers.
"""

from gymnasium        import Env, ObservationWrapper
from gymnasium.spaces import Box, Dict
from gymnasium.utils  import RecordConstructorArgs
from numpy            import ndarray, uint8

from squirtl.reward.schemas import Event


class ProgressObservation(ObservationWrapper, RecordConstructorArgs):
    """
    Observes beside the stacked frames the progress the reward reads, as
    Pleines et al. observe, each entry stacked along its first axis:

    - `flags`, one deep, from `Progress.flags`
    - `frames`, the stack the wrapped environment observes
    - `grid`, one deep, from `Progress.grid`, so the grid marks the
      positions the novelty term checks each step against
    """

    def __init__(self, env: Env, size: int):
        """
        Wraps `env`, whose observation is the stack of frames, laying out
        the grid `size` squares on a side.
        """
        RecordConstructorArgs.__init__(self, size=size)
        ObservationWrapper.__init__(self, env)

        self.observation_space = Dict(
            flags  = Box(0, 1, (1, len(Event)), uint8),
            frames = env.observation_space,
            grid   = Box(0, 1, (1, size, size), uint8)
        )
        self.size = size

    def observation(self, observation: ndarray) -> dict[str, ndarray]:
        """
        Sets the stacked frames `observation` holds beside the flags and the
        grid of the `Progress` the unwrapped environment keeps, read once
        the step or the reset that made `observation` has run.
        """
        progress = self.get_wrapper_attr("progress")

        return {
            "flags"  : progress.flags[None],
            "frames" : observation,
            "grid"   : progress.grid(self.size)[None]
        }
