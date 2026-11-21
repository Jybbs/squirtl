"""
Pins the arguments each `py` task hands the program it runs, meaning the
output format `py:lint` chooses for the shell it runs in, the coverage flags
`py:coverage` passes pytest, the test modules `py:affected` selects from the
files a branch changes, each further argument forwarded after the flags and
ahead of the operands, and the folders `py:lint` and `py:format` name as the
formatter's operands, beside the tests the reader in `reach.py` selects for
a changed module, helper, or root conftest.

The reader's cases import it through `load_task` and run it in a checkout
holding the files `SUITE` lists, with `tests/conftest.py` rewritten past its
one commit. The stand-in under `fixtures/` answers for `prose` and `pytest`,
printing each argument it receives on a line of its own, so no case starts
either program.
"""

from collections.abc import Callable, Mapping
from pathlib         import Path
from pytest          import CaptureFixture, fixture, mark, param
from types           import ModuleType

BASE = {
    ".mise/bin/pytest"    : "",
    ".mise/tasks/py/test" : "",
    "pyproject.toml"      : (
        '"--snapshot-default-extension=common.snapshots.PlainFile"\n'
        '"-p common.agents_pool"\n'
    ),
    "src/squirtl/agent/memory.py"       : "",
    "src/squirtl/cli/__init__.py"       : "",
    "src/squirtl/docs/references.bib"   : "@misc{sutton2018}\n",
    "tests/agent/conftest.py"           : '"docs/notes/readme.md"\n',
    "tests/agent/fixtures/memory/a.txt" : "from common.agents import each_agent\n",
    "tests/agent/learner.py"            : "from common.agents import each_agent\n",
    "tests/agent/memory.py"             : "def test_remembers(event):\n    pass\n",
    "tests/agent/networks.py"           : "import common.records as records\n",
    "tests/cli/app.py"           : "",
    "tests/cli/conftest.py"      : "from common.cli import Invoker\n",
    "tests/common/agents.py"     :
        '"docs/notes/license.md"\n"src/squirtl/search/tiles.bin"\n',
    "tests/common/cli.py"        : "from common.records import idled\n",
    "tests/common/console.py"    : "",
    "tests/common/evaluation.py" : '"docs/notes/citation.cff"\n',
    "tests/common/records.py"    : "from common.cli import Invoker\n",
    "tests/common/snapshots.py"  : "",
    "tests/conftest.py"          : (
        "from pytest import fixture\n\nfrom common.console import set_event\n\n\n"
        "@fixture\ndef event():\n    return set_event\n\n\n"
        '"docs/notes/setup.md"\n'
    ),
    "tests/evaluation/scores.py" : "from squirtl.agent.memory import Memory\n",
    "tests/repo/checks.py"       :
        '"src/squirtl/docs/references.bib"\n"src/squirtl/agent/layout.toml"\n',
    "tests/runs/trainer.py"      :
        "def test_trains():\n    from common.agents import each_agent\n",
    "tests/search/tree.py"       : "from common.agents_pool import each_pool\n",
    "tests/tasks/bin.py"         : "",
    "tests/tasks/py.py"          : ""
}
CONFTEST = '''"""
Shares the fixtures.
"""

from os     import devnull
from pytest import fixture

from squirtl.emulator.console import GameBoy
from squirtl.search.tree      import Tree

LIMIT = 3


@fixture(autouse=True)
def environment():
    """
    Isolates each test.
    """
    return Tree


@fixture
def clone(github):
    """
    Clones the repository.
    """
    return github


@fixture
def game():
    """
    Plays the game.
    """
    return GameBoy


@fixture
def github():
    """
    Serves each release.
    """
    return []


@fixture
def limited():
    """
    Caps the steps.
    """
    return LIMIT


@fixture
def null():
    """
    Names the null device.
    """
    return devnull


@fixture
def patched(monkeypatch):
    """
    Patches the press.
    """
    monkeypatch.setattr("squirtl.emulator.schemas.Button", None)


def pytest_collection_modifyitems(items):
    """
    Marks each test.
    """
'''
SUITE = {
    "pyproject.toml"              : '"-p common.plugin"\n',
    "src/squirtl/cli/__init__.py" : 'register("squirtl.cli.train:train")\n',
    "src/squirtl/cli/train.py"    : "",
    "src/squirtl/docs/regions.py" : "",
    "src/squirtl/emulator/console.py" : "",
    "src/squirtl/emulator/schemas.py" : "",
    "src/squirtl/reward/__init__.py"  : "from squirtl.reward.terms import Term\n",
    "src/squirtl/reward/terms.py"     : "",

    "src/squirtl/runs/loop.py": "from squirtl.runs.seeds import Seeds\n"
                                "from squirtl.runs.trainer import train\n",

    "src/squirtl/runs/seeds.py": "",

    "src/squirtl/runs/trainer.py":
        "def train():\n    from squirtl.runs.loop import run\n",

    "src/squirtl/search/__init__.py" : "",
    "src/squirtl/search/tree.py"     : "",
    "tests/cli/watch.py"             : "import squirtl.emulator.console as console\n",
    "tests/common/console.py"        : "from squirtl.emulator.console import GameBoy\n",
    "tests/common/plugin.py"         : "from common.terms import each_term\n",
    "tests/common/terms.py"          : "from squirtl.reward import Term\n",
    "tests/conftest.py"              : CONFTEST,
    "tests/docs/commands.py"         : "from squirtl.cli import app\n",

    "tests/docs/outputs.py": (
        "from pkgutil import iter_modules\n\nfrom squirtl import docs\n\n"
        "NAMES = [module.name for module in iter_modules(docs.__path__)]\n"
    ),

    "tests/docs/paths.py": "from squirtl import docs\n\nPATHS = [*docs.__path__]\n",
    "tests/emulator/console.py" : "from squirtl.emulator import console\n",
    "tests/reward/conftest.py"  : "from squirtl.emulator.console import GameBoy\n",
    "tests/reward/progress.py"  : "import os\n",
    "tests/runs/fixtures/handover/a.py": "import squirtl.emulator.console\n",

    "tests/runs/handover.py": """
from pytest import mark, param


@mark.usefixtures("game")
def test_plays():
    pass


def test_clones(clone):
    pass


@mark.parametrize("clone", [param([], id="empty")], indirect=True)
def test_clones_each(clone):
    pass


@mark.parametrize("clone", [param([], id="listed")], indirect=["clone"])
def test_clones_listed(clone):
    pass


@mark.parametrize(("github",), [param([], id="empty")])
def test_reads_a_release(github):
    pass


def test_caps(limited):
    pass


def test_names(null):
    pass


def test_patches(patched):
    pass


class TestOverride:

    @fixture
    def github(self):
        return {}

    def test_reads_its_own(self, github):
        pass
""",

    "tests/runs/marked.py": (
        'from pytest import mark\n\npytestmark = mark.usefixtures("limited")\n\n\n'
        "async def test_waits():\n    pass\n"
    ),

    "tests/runs/nulled.py": (
        "from pytest import fixture\n\n\n@fixture(autouse=True)\ndef nulled(null):\n"
        "    pass\n\n\ndef test_nulls():\n    pass\n"
    ),

    "tests/runs/trainer.py" : "from squirtl.runs.trainer import train\n",
    "tests/search/tree.py"  : "from common.console import set_event\n",

    "tests/search/workers.py":
        '"squirtl.emulator.console.GameBoy.press"\n"squirtl.unknown.name"\n',

    "tests/startup/imports.py":
        "WALK = 'for root in squirtl.__path__: import_module(root)'\n"
}


@fixture
def branch(
    checkout : Callable[[Mapping[str, str]], None],
    clone    : Path,
    git      : Callable[..., None]
) -> Callable[[bool, str], None]:
    """
    Builds a checkout whose `origin/main` holds each file `BASE` lists, and
    a function that changes one file on the branch past it, committed or
    left in the working tree.
    """
    def change(committed: bool, path: str):
        """
        Appends a line to the file at `path`, writing it where `BASE` holds
        none, and commits it where `committed` is set.
        """
        checkout({path: BASE.get(path, "") + "changed\n"})

        if committed:
            git("add", "--all")
            git("commit", "--message", "Change")

    checkout(BASE)
    git("add", "--all")
    git("commit", "--message", "Base")
    git("update-ref", "refs/remotes/origin/main", "HEAD")

    return change


@fixture(autouse=True)
def stand_in(install_stand_ins: Callable[..., Path]):
    """
    Puts the stand-in ahead of the real `prose` and `pytest` on the path for
    every case.
    """
    install_stand_ins("echo.sh", "prose", "pytest")


@mark.parametrize(
    ("task", "shell", "argv"),
    [
        param(
            "coverage",
            {},
            [
                "--cov", "--cov-report", "html", "--cov-report",
                "json", "--cov-report", "term", "--diff"
            ],
            id = "coverage"
        ),
        param(
            "format",
            {},
            ["format", "--diff", ".mise/tasks", "src", "tests"],
            id = "format"
        ),
        param(
            "lint",
            {},
            [
                "check", "--output-format", "text", "--diff",
                ".mise/tasks", "src", "tests"
            ],
            id = "lint-local"
        ),
        param(
            "lint",
            {"GITHUB_ACTIONS": "true"},
            [
                "check", "--output-format", "github", "--diff",
                ".mise/tasks", "src", "tests"
            ],
            id = "lint-actions"
        ),
        param("test", {}, ["--diff"], id="test")
    ],
    indirect = ["shell"]
)
def test_each_task_hands_its_program_its_flags_and_arguments(
    argv    : list[str],
    printed : Callable[..., list[str]],
    shell   : dict[str, str],
    task    : str
):
    """
    Pins the argument list each `py` task hands its program, with `py:lint`
    asking the formatter for annotations under GitHub Actions and for text
    elsewhere, and every task forwarding `--diff` after its own flags and
    ahead of any folders the formatter reads.
    """
    assert printed(f"py/{task}", "--diff") == argv


@mark.parametrize("committed", [False, True], ids=["uncommitted", "committed"])
@mark.parametrize(
    ("path", "modules"),
    [
        param(".mise/bin/pytest", ["tests/tasks/bin.py"], id="wrapper"),
        param(".mise/tasks/py/lint", ["tests/tasks/py.py"], id="task"),
        param("src/squirtl/docs/references.bib", ["tests/repo/checks.py"], id="named"),
        param("pyproject.toml", ["tests"], id="manifest"),
        param(
            "src/squirtl/agent/memory.py",
            ["tests/agent/memory.py", "tests/evaluation/scores.py"],
            id = "module"
        ),
        param("src/squirtl/cli/__init__.py", ["tests/cli/app.py"], id="app"),
        param(
            "src/squirtl/agent/layout.toml",
            ["tests/agent", "tests/repo/checks.py"],
            id = "package-file"
        ),
        param("tests/agent/conftest.py", ["tests/agent"], id="conftest"),
        param(
            "src/squirtl/search/tiles.bin",
            ["tests/agent/learner.py", "tests/runs/trainer.py", "tests/search"],
            id = "package-file-helper-named"
        ),
        param("docs/notes/readme.md", ["tests/agent"], id="conftest-named"),
        param("docs/notes/setup.md", ["tests"], id="root-conftest-named"),
        param(
            "tests/agent/fixtures/memory/a.txt",
            ["tests/agent/memory.py"],
            id = "snapshot"
        ),
        param("tests/agent/memory.py", ["tests/agent/memory.py"], id="test"),
        param(
            "tests/common/agents.py",
            ["tests/agent/learner.py", "tests/runs/trainer.py"],
            id = "helper"
        ),
        param(
            "docs/notes/license.md",
            ["tests/agent/learner.py", "tests/runs/trainer.py"],
            id = "helper-named"
        ),
        param(
            "tests/common/cli.py",
            ["tests/agent/networks.py", "tests/cli"],
            id = "conftest-helper"
        ),
        param(
            "tests/common/console.py",
            ["tests/agent/memory.py::test_remembers"],
            id = "root-conftest-helper"
        ),
        param(
            "tests/common/records.py",
            ["tests/agent/networks.py", "tests/cli"],
            id = "helper-helper"
        ),
        param("tests/common/snapshots.py", ["tests"], id="manifest-helper"),
        param("tests/conftest.py", ["tests"], id="root-conftest")
    ]
)
def test_affected_runs_the_test_modules_a_changed_file_reaches(
    branch    : Callable[[bool, str], None],
    committed : bool,
    modules   : list[str],
    path      : str,
    printed   : Callable[..., list[str]]
):
    """
    Pins the test modules, folders, and node IDs `py:affected` hands pytest
    for one file changed since the merge base with `origin/main`, whether
    committed, modified, or untracked, after the arguments it forwards.
    """
    branch(committed, path)

    assert printed("py/affected", "--diff") == ["--diff", *modules]


def test_affected_reaches_the_modules_naming_the_old_path_of_a_renamed_file(
    branch  : Callable[[bool, str], None],
    git     : Callable[..., None],
    printed : Callable[..., list[str]]
):
    """
    Pins that `py:affected` reads a committed rename as both of its paths,
    running the test module naming the path the file moved from.
    """
    git("mv", "src/squirtl/docs/references.bib", "src/squirtl/docs/sources.bib")
    git("commit", "--message", "Rename")

    assert printed("py/affected") == ["tests/repo/checks.py"]


@mark.parametrize(
    "first",
    [
        param("docs/glossary.md", id="unnamed"),
        param("tests/common/search.py", id="unimported-helper")
    ]
)
def test_affected_reads_each_changed_file_past_one_no_test_module_names(
    branch  : Callable[[bool, str], None],
    first   : str,
    printed : Callable[..., list[str]]
):
    """
    Pins that `py:affected` keeps reading the changed files past one no test
    module names and past a helper no module imports, running the module the
    file after it reaches.
    """
    branch(True, first)
    branch(True, "tests/repo/checks.py")

    assert printed("py/affected") == ["tests/repo/checks.py"]


def test_affected_reads_no_file_main_changed_past_the_merge_base(
    branch  : Callable[[bool, str], None],
    git     : Callable[..., None],
    printed : Callable[..., list[str]]
):
    """
    Pins that `py:affected` diffs the branch against its merge base with
    `origin/main` rather than its tip, so a file `main` changed after the
    branch left it reaches no test module.
    """
    git("switch", "--create", "next")
    branch(True, "src/squirtl/docs/references.bib")
    git("update-ref", "refs/remotes/origin/main", "HEAD")
    git("switch", "-")

    [line] = printed("py/affected")

    assert line.startswith("No test module reaches a file changed since ")


@mark.parametrize(
    "path",
    [
        param(None, id="unchanged"),
        param("src/squirtl/agent/replay.py", id="unmirrored"),
        param("tests/common/search.py", id="unimported-helper"),
        param("docs/notes/citation.cff", id="unimported-helper-named")
    ]
)
def test_affected_starts_no_pytest_where_no_test_module_is_reached(
    branch  : Callable[[bool, str], None],
    path    : str | None,
    printed : Callable[..., list[str]]
):
    """
    Pins that `py:affected` starts no pytest on a branch changing no file,
    and on one whose one changed file is a module with no mirrored test
    module, a helper no module imports, or a file only that helper names,
    since pytest given no path runs the whole suite.
    """
    if path:
        branch(False, path)

    [line] = printed("py/affected")

    assert line.startswith("No test module reaches a file changed since ")


@fixture
def reach(
    checkout  : Callable[[Mapping[str, str]], None],
    git       : Callable[..., None],
    load_task : Callable[[str], ModuleType]
) -> Callable[..., list[str]]:
    """
    Builds a checkout whose one commit holds each file `SUITE` lists, and a
    function rewriting `tests/conftest.py` past it before returning what the
    `py:affected` reader selects for the changed paths it receives.

    Returns:
        A function taking the conftest's text in the working tree and then
        the changed paths, which returns the reader's selection, or
        `["tests"]` where a change reaches every test.
    """
    checkout(SUITE)
    git("init", "--quiet")
    git("add", "--all")
    git("commit", "--message", "Base", "--quiet")

    def select(conftest: str, *changed: str) -> list[str]:
        """
        Writes `conftest` as `tests/conftest.py` and reads the selection.
        """
        checkout({"tests/conftest.py": conftest})
        return load_task(".mise/tasks/py/reach.py").Suite.read().select(
            "HEAD", changed
        )

    return select


@mark.parametrize(
    ("changed", "selected"),
    [
        param(
            "src/squirtl/emulator/console.py",
            [
                "tests/cli/watch.py", "tests/emulator/console.py", "tests/reward",
                "tests/runs/handover.py::test_plays", "tests/search/tree.py",
                "tests/search/workers.py", "tests/startup/imports.py"
            ],
            id = "module"
        ),
        param(
            "src/squirtl/emulator/schemas.py",
            ["tests/runs/handover.py::test_patches", "tests/startup/imports.py"],
            id = "quoted-in-root-fixture"
        ),
        param(
            "src/squirtl/runs/seeds.py",
            ["tests/runs/trainer.py", "tests/startup/imports.py"],
            id = "loaded-through-a-function-local-import-and-a-cycle"
        ),
        param(
            "src/squirtl/docs/regions.py",
            ["tests/docs/outputs.py", "tests/startup/imports.py"],
            id = "under-a-walked-package"
        ),
        param("src/squirtl/reward/terms.py", ["tests"], id="reexported-to-plugin"),
        param("tests/common/terms.py", ["tests"], id="plugin-helper"),
        param("tests/common/removed.py", ["tests"], id="removed"),
        param("src/squirtl/search/tree.py", ["tests"], id="read-by-autouse"),
        param("src/squirtl/search/__init__.py", ["tests"], id="package-of-root-import"),
        param(
            "tests/common/console.py",
            ["tests/search/tree.py"],
            id = "helper-unread-by-root-fixtures"
        ),
        param(
            "src/squirtl/cli/train.py",
            ["tests/docs/commands.py", "tests/startup/imports.py"],
            id = "loaded-by-package-init"
        )
    ]
)
def test_reach_selects_the_tests_importing_a_changed_module(
    changed  : str,
    reach    : Callable[..., list[str]],
    selected : list[str]
):
    """
    Pins that the `py:affected` reader selects each test module importing
    a changed module directly, through a package `__init__`, a helper, a
    quoted name, a package `__init__` under `src/` quoting it, or a chain
    of package modules, a function-local import and a cycle included, each
    test module walking a package holding it by computed name, the folder
    of a subpackage conftest importing it, and the tests requesting a root
    fixture reading a name the root conftest binds to it, while a removed
    file, a helper `pyproject.toml` loads as a plugin, a name the autouse
    fixture reads, and a package `__init__` the root conftest loads on the
    way reach every test, and a module under `fixtures/` reaches none.
    """
    assert reach(CONFTEST, changed) == selected


@mark.parametrize(
    ("old", "new", "selected"),
    [
        param(
            "    return []\n",
            "    return [1]\n",
            [
                "tests/runs/handover.py::test_clones",
                "tests/runs/handover.py::test_clones_each",
                "tests/runs/handover.py::test_clones_listed"
            ],
            id = "fixture-and-its-requester"
        ),
        param("Serves each release.", "Serves every release.", [], id="docstring"),
        param(
            "Shares the fixtures.",
            "Shares each fixture.",
            [],
            id = "module-docstring"
        ),
        param(
            "from os     import devnull",
            "from os.path import devnull",
            ["tests/runs/handover.py::test_names", "tests/runs/nulled.py::test_nulls"],
            id = "rebound-import"
        ),
        param(
            "from os     import devnull",
            "from os import devnull, sep",
            [],
            id = "added-import"
        ),
        param(
            '    """\n    Isolates each test.\n    """\n',
            "    pass\n",
            ["tests"],
            id = "autouse"
        ),
        param(
            '    Marks each test.\n    """\n',
            '    """\n    del items\n',
            ["tests"],
            id = "hook"
        ),
        param("LIMIT = 3", "LIMIT = 4", ["tests"], id="name-a-fixture-reads"),
        param(
            "LIMIT = 3",
            'LIMIT = 3\npytest_plugins = ["common.terms"]',
            ["tests"],
            id = "plugins"
        ),
        param(
            "\n\n@fixture\ndef null",
            "\n\nprint()\n\n\n@fixture\ndef null",
            ["tests"],
            id = "statement"
        ),
        param(
            "@fixture\ndef limited():",
            '@fixture(scope="session")\ndef limited():',
            ["tests/runs/handover.py::test_caps", "tests/runs/marked.py::test_waits"],
            id = "decorator"
        )
    ]
)
def test_reach_selects_the_tests_requesting_a_changed_root_fixture(
    new      : str,
    old      : str,
    reach    : Callable[..., list[str]],
    selected : list[str]
):
    """
    Pins that the `py:affected` reader selects, for a change to
    `tests/conftest.py`, the tests requesting a fixture whose definition the
    change touches or that reads a name an import line binds anew, none for
    a docstring or a binding no fixture reads, and every test for a change
    to the autouse fixture, a hook, `pytest_plugins`, a name a fixture
    reads, or any other statement.
    """
    assert old in CONFTEST

    assert reach(CONFTEST.replace(old, new), "tests/conftest.py") == selected


def test_reach_prints_each_selection_or_every_test(
    capsys    : CaptureFixture[str],
    load_task : Callable[[str], ModuleType],
    reach     : Callable[..., list[str]]
):
    """
    Pins that the `py:affected` reader prints one selection a line, nothing
    where no test is reached, and `tests` alone once a change reaches every
    test.
    """
    module = load_task(".mise/tasks/py/reach.py")

    module.main("HEAD")
    module.main("HEAD", "tests/common/console.py")
    module.main("HEAD", "tests/common/terms.py")

    assert capsys.readouterr().out == "tests/search/tree.py\ntests\n"


def test_reach_selects_every_test_where_the_root_conftest_walks_a_changed_module(
    reach: Callable[..., list[str]]
):
    """
    Pins that the `py:affected` reader selects every test where
    `tests/conftest.py` walks the package holding a changed module through
    `pkgutil.walk_packages`, since no fixture is bound to what it loads.
    """
    assert reach(
        CONFTEST + "\n\nfrom pkgutil import walk_packages\n\nimport squirtl\n"
        "\nNAMES = [*walk_packages(squirtl.__path__)]\n",
        "src/squirtl/docs/regions.py"
    ) == ["tests"]


def test_reach_selects_the_tests_requesting_a_removed_root_fixture(
    reach: Callable[..., list[str]]
):
    """
    Pins that the `py:affected` reader selects the tests still requesting a
    fixture `tests/conftest.py` no longer defines, through the side of the
    change that defined it, leaving out a test whose class overrides it.
    """
    github, limited = (CONFTEST.index(f"@fixture\ndef {name}") for name in (
        "github", "limited"
    ))

    assert reach(
        CONFTEST[:github] + CONFTEST[limited:],
        "tests/conftest.py"
    ) == [
        "tests/runs/handover.py::test_clones",
        "tests/runs/handover.py::test_clones_each",
        "tests/runs/handover.py::test_clones_listed"
    ]
