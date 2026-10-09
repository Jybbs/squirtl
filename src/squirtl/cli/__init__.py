"""
Exposes the `squirtl` command, whose help prints the summary the package
metadata carries beneath its usage line and whose `--version` flag prints
the version that metadata names. A command takes each setting from the flag
passed for it, then from the `[tool.squirtl]` table of the `pyproject.toml`
in the working directory, and otherwise from the default its field declares.
"""

from cyclopts           import App, Parameter
from cyclopts.config    import Toml
from importlib.metadata import metadata

app = App(
    config = Toml(
        "pyproject.toml",
        root_keys            = ("tool", "squirtl"),
        use_commands_as_keys = False
    ),
    default_parameter = Parameter(negative=()),
    help              = metadata("squirtl")["Summary"],
    name              = "squirtl"
)
