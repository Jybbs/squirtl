"""
Defines `ignore_interrupts`, the worker each environment of an evaluation
runs in a process of its own, which imports nothing beyond what that worker
needs, since a spawned process imports the module its worker sits in.
"""

from gymnasium.vector.async_vector_env import _async_worker
from signal import SIGINT, SIG_IGN, signal


def ignore_interrupts(*arguments: object):
    """
    Ignores the interrupt signal, which a terminal sends every process
    in its foreground group, then runs Gymnasium's own worker, so a first
    interrupt reaches only the main process, whose handler under `squirtl
    train` ends the run at its episode's end.
    """
    signal(SIGINT, SIG_IGN)
    _async_worker(*arguments)
