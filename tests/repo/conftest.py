"""
Defines the fixtures the tests of `squirtl.repo` share, meaning the text of
a manifest declaring every key the records of the subpackage read and the
text of the `.mise/config.toml` its pins are held to.
"""

from pytest   import fixture
from textwrap import dedent


@fixture
def manifest() -> str:
    """
    Builds the text of a `pyproject.toml` declaring every key the records
    of `squirtl.repo` read, each at a value every check passes against the
    `.mise/config.toml` that `mise_config` builds.
    """
    return dedent(
        """
        [build-system]
        requires = ["hatchling==1.32.4"]

        [project]
        authors         = [{ name = "Ash Ketchum" }]
        description     = "Plays."
        keywords        = ["dqn", "pyboy"]
        license         = "MIT"
        license-files   = ["LICENSE.md"]
        name            = "squirtl"
        requires-python = ">=3.14"
        version         = "0.1.0"

        [project.scripts]
        squirtl = "squirtl.cli:app"

        [tool.hatch.build.targets.wheel]
        packages = ["src/squirtl"]

        [tool.prose]
        target-version = "3.14"

        [tool.pytest]
        norecursedirs = ["common", "fixtures"]
        python_files  = ["*.py"]
        testpaths     = ["tests"]

        [tool.uv]
        build-constraint-dependencies = ["packaging==26.3"]
        required-version              = "==0.12.13"
        """
    )


@fixture
def mise_config() -> str:
    """
    Builds the text of a `.mise/config.toml` pinning Node.js 26.12.1, Python
    3.14.6, and uv 0.12.13, the pins `manifest` and the site's manifest a
    case writes each repeat.
    """
    return '[tools]\nnode = "26.12.1"\npython = "3.14.6"\nuv = "0.12.13"\n'
