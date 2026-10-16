"""
Holds what each command reports through:

- `listen`, which sends loguru's lines through a console writing to standard
  error, the console a progress bar shares so each line prints above it
- `refusing`, which turns an error a command's input raises into one logged
  line and exit status 1
"""

from collections.abc import Iterator
from contextlib      import contextmanager
from loguru          import logger
from rich.console    import Console


def listen(verbose: bool = False) -> Console:
    """
    Removes every place loguru writes its lines, then adds a console writing
    to standard error as the one place it writes them, from `DEBUG` up where
    `verbose` is set and from `INFO` up otherwise.

    Returns:
        The console, which reads `sys.stderr` as it writes each line, so a
        line reaches whatever stream is current when a command runs.
    """
    console = Console(stderr=True)

    logger.remove()
    logger.add(
        lambda line: console.out(line, end="", highlight=False),
        format = "{time:HH:mm:ss} {message}",
        level  = "DEBUG" if verbose else "INFO"
    )

    return console


@contextmanager
def refusing(*errors: type[Exception]) -> Iterator[None]:
    """
    Logs any of `errors` the block raises as one error line and exits with
    status 1 in place of a traceback.

    Raises:
        SystemExit: Where the block raises one of `errors`.
    """
    try:
        yield
    except errors as error:
        logger.error("{}", error)

        raise SystemExit(1) from None
