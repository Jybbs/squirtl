"""
Pins what `squirtl write docs` does, covering the files it writes into a
checkout missing them, the path of each it prints, and a second run printing
nothing once every file matches its declaration.
"""

from common.cli import Invoker
from pytest     import mark

from squirtl.docs.outputs import Inventory


@mark.usefixtures("outside")
def test_writing_docs_writes_each_file_once_and_prints_its_path(invoke: Invoker):
    """
    Asserts that the command writes every file the inventory lists into a
    checkout holding none of them, printing each path, and that a second run
    finds nothing drifted and prints nothing.
    """
    paths = [str(output.path) for output in Inventory.read().outputs]

    first  = invoke(["write", "docs"])
    second = invoke(["write", "docs"])

    assert (first.code, first.output.splitlines()) == (0, paths)
    assert (second.code, second.output) == (0, "")
