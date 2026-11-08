"""
Loads imports lazily in each interpreter of the virtual environment
the package is installed in, through the `squirtl.start` file the wheel
installs, which names `start` as the callable the interpreter runs before
the program it was asked to run. A package's own imports load eagerly where
`EAGER` names the package.

A lift of a package `EAGER` names rechecks its entry under a filter leaving
the entry out, and removes the entry once its error no longer reproduces.
The recheck loads the package through `importlib.import_module`, since an
`import` statement under the lazy mode loads nothing until a name it binds
is read, or runs `mise test` for `_pytest`.
"""

from sys import set_lazy_imports, set_lazy_imports_filter

EAGER = frozenset({
    # ImportCycleError: cannot import name 'fnmatch'
    "_pytest",
    # AttributeError: 'FPContext' object has no attribute 'zetazero'
    "mpmath",
    # AttributeError: Attribute 'Catalan' was not installed on SymPy registry S
    "sympy",
    # ImportError: cannot import name 'is_custom_class' from partially
    # initialized module 'torch._library.opaque_object'
    "torch"
})
"""
The top-level packages whose own imports load eagerly, each above the error
its lazy imports raise.
"""


def lazily(importer: str | None, *_: object) -> bool:
    """
    Keeps an import lazy unless the module making it sits in a package
    `EAGER` names, where `importer` is `None` for an import no module makes.
    """
    return importer is None or importer.partition(".")[0] not in EAGER


def start():
    """
    Sets the filter, then turns on the lazy mode for every import the filter
    leaves lazy.
    """
    set_lazy_imports_filter(lazily)
    set_lazy_imports("all")
