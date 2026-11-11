"""
Defines `each_agent`, which parametrizes a test over `algorithm`, PQN and
PPO.
"""

from pytest import mark, param

from squirtl.agent.schemas import Algorithm

each_agent = mark.parametrize(
    "algorithm",
    [param(Algorithm.PPO, id="ppo"), param(Algorithm.PQN, id="pqn")]
)
