"""
Defines `starts_processes`, the `xdist_group` mark sending every test that
starts worker processes of its own to one pytest-xdist worker, which runs
one such test at a time, so the pools a run starts never multiply against
the workers.
"""

from pytest import mark

starts_processes = mark.xdist_group("processes")
