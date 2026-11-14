"""
Pins how each interpreter of the virtual environment loads its
imports, covering:

- The filter's verdict on an importer inside and outside `EAGER`
- The mode and the filter `start` sets
- The mode and the filter an interpreter of the virtual environment starts
  under, and the normal mode one started without `site` keeps
- Every module of the package importing under the normal mode, which a cycle
  among them breaks while the lazy mode hides it
"""

from importlib  import reload
from pytest     import mark, param
from subprocess import check_output
from sys        import executable, get_lazy_imports, get_lazy_imports_filter

from squirtl.startup import imports

PROBE = (
    "from sys import get_lazy_imports as mode, get_lazy_imports_filter as read\n"
    "print(mode(), getattr(read(), '__qualname__', None))"
)
"""
The program a started interpreter runs, printing its mode and its filter's
name.
"""

WALK = (
    "from importlib import import_module\n"
    "from pkgutil import walk_packages\n"
    "from sys import set_lazy_imports\n"
    "set_lazy_imports('normal')\n"
    "import squirtl\n"
    "for module in walk_packages(squirtl.__path__, 'squirtl.'):\n"
    "    try:\n"
    "        import_module(module.name)\n"
    "    except ImportError as error:\n"
    "        print(module.name, error)"
)
"""
The program a started interpreter runs, turning the lazy mode off before
importing each module of the package and printing each that fails with its
error.
"""


def test_every_module_of_the_package_imports_under_the_normal_mode():
    """
    Asserts that each module under `squirtl` imports in an interpreter whose
    lazy mode is turned off, so no import cycle among the package's modules
    loads only because the start file defers it.
    """
    assert check_output([executable, "-c", WALK], text=True) == ""


@mark.parametrize(
    ("flags", "expected"),
    [
        param((),     "all lazily",  id="through-site"),
        param(("-S",), "normal None", id="without-site")
    ]
)
def test_an_interpreter_of_the_virtual_environment_starts_under_the_start_file(
    flags    : tuple[str, ...],
    expected : str
):
    """
    Asserts that an interpreter started with no environment variables takes
    the mode and the filter from the installed start file, and that `-S`,
    which skips the `site` module that reads that file, keeps the normal
    mode.
    """
    assert check_output(
        [executable, *flags, "-c", PROBE],
        env  = {},
        text = True
    ).strip() == expected


def test_start_sets_the_mode_and_the_filter():
    """
    Asserts that `start`, run from a reloaded module since `site` loads it
    before coverage starts, sets the filter and turns on the lazy mode.
    """
    module = reload(imports)

    module.start()

    assert get_lazy_imports() == "all"
    assert get_lazy_imports_filter() is module.lazily


@mark.parametrize(
    ("importer", "expected"),
    [
        param(None,                 True,  id="no-importer"),
        param("squirtl.agent.deep", True,  id="the-package"),
        param("torchvision.io",     True,  id="a-name-opening-on-an-entry"),
        param("torch",              False, id="an-entry-itself"),
        param("torch.nn.functional", False, id="a-submodule-of-an-entry"),
        param("_pytest.config",     False, id="the-suites-entry")
    ]
)
def test_the_filter_keeps_an_import_lazy_outside_the_excepted_packages(
    importer : str | None,
    expected : bool
):
    """
    Asserts that the filter reads the importer's top-level package alone,
    whatever the import names.
    """
    assert imports.lazily(importer, "torch", None) is expected
