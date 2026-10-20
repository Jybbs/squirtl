"""
Exposes the `squirtl` command, whose help prints the summary the package
metadata carries beneath its usage line and whose `--version` flag prints
the version that metadata names. `squirtl train` takes each setting
from the flag passed for it, then from the `[tool.squirtl]` table of the
`pyproject.toml` in the working directory, and otherwise from the default
its field declares, whereas every other command reads the settings its run
recorded and so reads no such table.
"""

from cyclopts           import App, Parameter
from cyclopts.config    import Toml
from importlib.metadata import metadata

from squirtl.cli.evaluate import evaluate
from squirtl.cli.stop     import stop
from squirtl.cli.train    import train
from squirtl.cli.watch    import watch

app = App(
    default_parameter = Parameter(negative=()),
    help              = metadata("squirtl")["Summary"],
    name              = "squirtl"
)

app.command(evaluate)
app.command(stop)
app.command(
    train,
    config = Toml(
        "pyproject.toml",
        root_keys            = ("tool", "squirtl"),
        use_commands_as_keys = False
    )
)
app.command(watch)
