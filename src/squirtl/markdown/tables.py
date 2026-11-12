"""
Lays out each Markdown table the package writes, the tables `squirtl
evaluate` prints and the tables `squirtl write docs` writes into the site's
pages alike, through `tabulate`.
"""

from collections.abc import Iterable


def tabulate(header: Iterable[str], rows: Iterable[Iterable[object]]) -> str:
    """
    Lays out a Markdown table, the bolded `header` and its rule over a line
    for each row of `rows`, each cell written as `str` writes it.
    """
    names = [f"**{name}**" for name in header]
    lines = (f"| {' | '.join(map(str, cells))} |" for cells in (names, *rows))

    return "\n".join((next(lines), "|" + "---|" * len(names), *lines))
