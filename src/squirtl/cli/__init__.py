"""
Exposes the `squirtl` command, whose help prints the summary the package
metadata carries beneath its usage line and whose `--version` flag prints
the version that metadata names. Each command's module loads only where
the command line names that command or an unknown command's error lists
them all, and `squirtl --help` reads each summary from the module's source.
`squirtl train` takes each setting from the flag passed for it, then from
the `[tool.squirtl]` table of the `pyproject.toml` in the working directory,
and otherwise from the default its field declares, whereas a command reading
a run takes the settings that run recorded, and no other command reads that
table. Passed after any command or group beneath `squirtl`, the `--version`
flag prints that same version.
"""

from ast                import FunctionDef, get_docstring, parse
from cyclopts           import App, Parameter
from cyclopts.config    import Toml
from functools          import partial
from importlib.metadata import metadata, version
from importlib.util     import find_spec
from pathlib            import Path


def register(group: App, target: str, **options: object):
    """
    Registers the function `target` names, as `module:function`, as a
    command of `group`, taking its help from the function's docstring in the
    module's source. The module loads only where the command line names the
    command or an unknown command's error lists them all.
    """
    module, name = target.split(":")
    function     = next(
        node
        for node in parse(
            Path(find_spec(module).origin).read_text(encoding="utf-8")
        ).body
        if isinstance(node, FunctionDef) and node.name == name
    )

    group.command(target, help=get_docstring(function), **options)


app = App(
    default_parameter = Parameter(negative=()),
    help              = metadata("squirtl")["Summary"],
    name              = "squirtl",
    version           = partial(version, "squirtl")
)

register(app, "squirtl.cli.cite:cite")
register(app, "squirtl.cli.evaluate:evaluate")
register(app, "squirtl.cli.fetch:fetch")
register(app, "squirtl.cli.pack:pack")
register(app, "squirtl.cli.stop:stop")
register(
    group  = app,
    target = "squirtl.cli.train:train",
    config = Toml(
        "pyproject.toml",
        root_keys            = ("tool", "squirtl"),
        use_commands_as_keys = False
    )
)
register(app, "squirtl.cli.watch:watch")
app.command(
    App(help="Writes files the package declares into the checkout.", name="write")
)
register(app["write"], "squirtl.cli.write:docs")
