"""
Defines `EAGERLY`, the lines an interpreter of its own runs before importing
the package, so every import of a `squirtl` module loads where it is written
while every other import keeps the filter the start file set.
"""

EAGERLY = (
    "from sys import get_lazy_imports_filter, set_lazy_imports_filter\n"
    "kept = get_lazy_imports_filter()\n"
    "set_lazy_imports_filter(\n"
    "    lambda importer, name, names: name.partition('.')[0] != 'squirtl'\n"
    "    and kept(importer, name, names)\n"
    ")\n"
)
"""
The program that wraps the start file's filter in one forcing each import
of a `squirtl` module to load eagerly, leaving the lazy mode as it was.
"""
