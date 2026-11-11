"""
Defines `docs`, the `squirtl write docs` command the `docs:write` task
runs, which writes every file the package declares into `docs/` and every
footnote definition `docs/references.bib` declares into each Markdown file
git tracks.
"""

from subprocess import SubprocessError

from squirtl.cli.logs     import listen, refusing
from squirtl.docs.outputs import Inventory
from squirtl.docs.schemas import Bibliography, Manuscripts


def docs():
    """
    Writes each file the site reads from a declaration in the package into
    `docs/` where it differs from that declaration, the identity's JSON
    among them, and closes each Markdown file git tracks on the definition
    of each source it cites, printing the path of each file it wrote.

    A marker naming a key `docs/references.bib` does not declare exits 1
    before any file is written, naming the file and the line, as does a
    Markdown file that cites a source and ends inside an open block, such
    as an unclosed code fence, naming the line the block opens on, and a
    `docs/references.bib` that fails to read, naming its line. A marker
    under `docs/pages/` left unpaired, or a run under `docs/runs/` that
    read another cartridge, followed a demonstration at an absolute path,
    or holds no evaluation of the agent or the random baseline, exits 1 once
    the footnotes are written and before any other file is, naming the page
    and the line or the run, as does a command's page whose markers do not
    hold the parts written from its help in order, naming the page.
    """
    listen()

    with refusing(LookupError, OSError, SubprocessError, SyntaxError, ValueError):
        manuscripts = Manuscripts.read().write(Bibliography.read())
        inventory   = Inventory.read()

    for path in (*manuscripts, *inventory.write()):
        print(path)
