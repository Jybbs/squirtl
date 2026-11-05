"""
Defines `cite`, the command that prints the footnote definition of each
source `docs/references.bib` declares under a given key.
"""

from squirtl.cli.logs     import listen, refusing
from squirtl.docs.schemas import Bibliography


def cite(keys: list[str]):
    """
    Prints the footnote definition of each given key in the order given, a
    blank line between two, for the body of an issue or a pull request.

    A key that `docs/references.bib` does not declare and a file that fails
    to read each exit 1, and a call naming no key exits 2, each printing
    no definition.

    Args:
        keys: The keys to print, each a lowercase surname and year.
    """
    listen()

    with refusing(LookupError, OSError, SyntaxError):
        print("\n\n".join(Bibliography.read().cite(*keys)))
