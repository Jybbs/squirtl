"""
Holds what each command reports through:

- `listen`, which sends loguru's lines through a console writing to standard
  error, the console a progress bar shares so each line prints above it
- `refusing`, which turns an error a command's input raises into one logged
  line per reason it gives and exit status 1
"""

from collections.abc import Iterator
from contextlib      import contextmanager
from loguru          import logger
from pydantic        import ValidationError
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
    Logs any of `errors` the block raises and exits with status 1 in place
    of a traceback. It logs one line per error a `ValidationError` holds,
    the exception a validator raised or else the path to the field beside
    Pydantic's message (`Run.revision: Field required`), and one line
    holding the message of any other error.

    Raises:
        SystemExit: Where the block raises one of `errors`.
    """
    try:
        yield
    except errors as error:
        match error:
            case ValidationError():
                for detail in error.errors(include_input=False, include_url=False):
                    match detail:
                        case {"ctx": {"error": Exception() as raised}}:
                            logger.error("{}", raised)
                        case {"loc": location, "msg": message}:
                            logger.error(
                                "{}: {}",
                                ".".join(map(str, (error.title, *location))),
                                message
                            )
            case _: logger.error("{}", error)

        raise SystemExit(1) from None
