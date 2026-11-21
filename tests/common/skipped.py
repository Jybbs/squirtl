"""
Defines the pytest plugin the `py:snapshots` task loads by its module path,
which skips every collected test. syrupy then reads each test as selected
and skipped, keeps every snapshot a collected test bears the name of, and
fails the run on any other snapshot.
"""

from pytest import Item, mark


def pytest_collection_modifyitems(items: list[Item]):
    """
    Marks every collected test to skip before it runs.
    """
    for item in items:
        item.add_marker(mark.skip(reason="py:snapshots runs no test"))
