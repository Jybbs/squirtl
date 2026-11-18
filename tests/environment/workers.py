"""
Pins the worker each environment of an evaluation or of a run of PQN or PPO
runs in, which ignores the interrupt signal before it runs Gymnasium's own
worker on the arguments it was given.
"""

from contextlib import ExitStack
from pytest     import MonkeyPatch
from signal     import SIGINT, SIG_IGN, getsignal, signal

from squirtl.environment import workers


def test_the_worker_ignores_interrupts_then_runs_gymnasiums_own(
    monkeypatch: MonkeyPatch
):
    """
    Asserts that the worker sets the interrupt signal to be ignored before
    Gymnasium's worker starts, then hands that worker every argument it
    took.
    """
    started = []
    monkeypatch.setattr(
        workers,
        "_async_worker",
        lambda *arguments: started.append((arguments, getsignal(SIGINT)))
    )

    with ExitStack() as stack:
        stack.callback(signal, SIGINT, getsignal(SIGINT))
        workers.ignore_interrupts(0, "pipe", "queue")

    assert started == [((0, "pipe", "queue"), SIG_IGN)]
