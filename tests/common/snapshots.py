"""
Defines `PlainFile`, the syrupy extension the `--snapshot-default-extension`
option in `[tool.pytest]` names for every snapshot the suite writes.
"""

from syrupy.extensions.single_file import SingleFileSnapshotExtension, WriteMode


class PlainFile(SingleFileSnapshotExtension):
    """
    Writes each snapshot as a plain text file at
    `fixtures/<module>/<test>.txt` beside the tests that read it, the
    `fixtures` directory named by the `--snapshot-dirname` option in
    `[tool.pytest]`.

    syrupy looks for unused snapshots only under `fixtures/<module>/`
    through this extension, so an input file a test reads from `fixtures/`
    itself never reads as a snapshot nobody used.
    """

    _write_mode    = WriteMode.TEXT
    file_extension = "txt"
