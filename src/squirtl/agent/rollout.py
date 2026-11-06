"""
Defines `Rollout`, the steps PQN and PPO collect across their environments
between two updates, from which one pass backward computes the λ-return of
every step.
"""

from collections.abc        import Mapping
from gymnasium.spaces       import Dict
from gymnasium.vector.utils import batch_space, create_empty_array
from numpy import bool_, concatenate, empty_like, float32, int64, ndarray, where, zeros
from torch import Tensor, as_tensor


class Rollout:
    """
    The steps each environment takes between two updates, each array holding
    one row per step and one column per environment. The arrays run from
    the observation each step acted on to the value of the final observation
    where the step truncated an episode, and `row` names the row the step
    under way writes.
    """

    def __init__(self, environments: int, space: Dict, steps: int):
        """
        Allocates `steps` rows of `environments` columns for each array, the
        observations' entries as `space` declares them.
        """
        shape = (steps, environments)

        self.actions      = zeros(shape, int64)
        self.bootstraps   = zeros(shape, float32)
        self.log_probs    = zeros(shape, float32)
        self.observations = create_empty_array(batch_space(space, environments), steps)
        self.rewards      = zeros(shape, float32)
        self.row          = 0
        self.terminated   = zeros(shape, bool_)
        self.truncated    = zeros(shape, bool_)
        self.values       = zeros(shape, float32)

    def batch(self, device: str, returns: ndarray) -> dict[str, Tensor]:
        """
        Moves what an update reads onto `device`, the entries of the
        observations, the actions, their log-probabilities, the values, and
        `returns`, each with every step along one axis.
        """
        arrays = self.observations | {
            "actions"   : self.actions,
            "log_probs" : self.log_probs,
            "returns"   : returns,
            "values"    : self.values
        }

        return {
            name: as_tensor(array, device=device).flatten(0, 1)
            for name, array in arrays.items()
        }

    def returns(self, decay: float, discount: float, last: ndarray) -> ndarray:
        """
        Computes each step's λ-return in one pass backward over the rollout,
        the reward plus `discount` times the value of the observation the
        step reached, mixed with the λ-return of the step after it at a
        weight of `decay`. No later λ-return reaches a step that ended its
        episode, where an episode that terminated adds no value and one that
        truncated adds the value of its final observation, as Pardo et al.
        bootstrap a time limit. The last step reads `last`, the value of the
        observation each environment reached.

        Args:
            decay : The λ weighting each later λ-return.
            last  : A `(environments,)` array of values.

        Returns:
            A `(steps, environments)` array of `float32`.
        """
        reached = where(
            self.truncated,
            self.bootstraps,
            concatenate([self.values[1:], last[None]])
        )
        ended   = self.terminated | self.truncated
        returns = empty_like(self.rewards)
        ahead   = reached[-1]

        for row in reversed(range(len(returns))):
            mixed = reached[row] + decay * ~ended[row] * (ahead - reached[row])
            ahead = returns[row] = (
                self.rewards[row] + discount * ~self.terminated[row] * mixed
            )

        return returns

    def store_action(
        self,
        *,
        actions      : ndarray,
        log_probs    : ndarray | None,
        observations : Mapping[str, ndarray],
        values       : ndarray
    ):
        """
        Writes into `row` the observations its step acted on, the
        actions it took, the value of each observation, and, for PPO, the
        log-probability of each action, which PQN leaves as `None`.
        """
        for key, entry in observations.items():
            self.observations[key][self.row] = entry

        self.actions[self.row] = actions
        self.values[self.row]  = values

        if log_probs is not None:
            self.log_probs[self.row] = log_probs

    def store_outcome(
        self,
        *,
        bootstraps : ndarray,
        rewards    : ndarray,
        terminated : ndarray,
        truncated  : ndarray
    ):
        """
        Writes into `row` the reward its step earned in each environment,
        whether it terminated or truncated the episode, and the value of
        each truncated episode's final observation, 0 for any other, then
        moves on to the next row.
        """
        self.bootstraps[self.row] = bootstraps
        self.rewards[self.row]    = rewards
        self.terminated[self.row] = terminated
        self.truncated[self.row]  = truncated
        self.row                 += 1
