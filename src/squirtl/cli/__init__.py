"""
Exposes the `squirtl` command, whose help prints the summary the package
metadata carries beneath its usage line and whose `--version` flag prints
the version that metadata names.
"""

from cyclopts           import App, Parameter
from importlib.metadata import metadata

app = App(
    default_parameter = Parameter(negative=()),
    help              = metadata("squirtl")["Summary"],
    name              = "squirtl"
)
