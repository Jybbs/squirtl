"""
Defines `docs`, the `squirtl write docs` command the `docs:write` task runs,
which writes every file the package declares into `docs/`.
"""

from squirtl.docs.outputs import Inventory


def docs():
    """
    Writes each file the site reads from a declaration in the package into
    `docs/` where it differs from that declaration, the identity's JSON
    among them, and prints the path of each file it wrote.
    """
    for path in Inventory.read().write():
        print(path)
