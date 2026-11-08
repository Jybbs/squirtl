"""
Loads imports lazily in each process of the environment, through the
`squirtl.start` file the wheel installs, which names `start` as the callable
the interpreter runs before the program it was asked to run. A package's own
imports load eagerly where `EAGER` names the package.

A lift of a package `EAGER` names rechecks its entry by importing the
package, or by running `mise test` for `_pytest`, under a filter leaving the
entry out, and removes the entry once its error no longer reproduces.
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
