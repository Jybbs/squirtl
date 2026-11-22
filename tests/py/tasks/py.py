"""
Pins the arguments each `py` task hands the program it runs, meaning the
output format `py:lint` chooses for the shell it runs in, the coverage flags
`py:coverage` and `py:split` pass pytest, the plugin `py:snapshots` loads,
the test modules `py:affected` selects from the files a branch changes,
each further argument forwarded after the flags and ahead of the operands,
and the folders `py:lint` and `py:format` name as the formatter's operands,
beside the tests the reader in `reach.py` selects for a changed module,
helper, or root conftest, the verdict `py:combine` reaches from the parts
it combines, and the unused snapshots syrupy still fails on once the plugin
`py:snapshots` loads skips every test.

The reader's and `py:combine`'s cases import each script through
`load_task`, the reader's running in a checkout holding the files `SUITE`
lists, with `tests/py/conftest.py` rewritten past its one commit. The
stand-in under `fixtures/` answers for `prose` and `pytest`, printing each
argument it receives on a line of its own, so no task case starts either
program, whereas the plugin's cases start pytest in an interpreter of their
own over a module written under `tmp_path`.
"""

from collections.abc import Callable, Mapping
from coverage        import CoverageData
from json            import loads
from pathlib         import Path
from pytest          import CaptureFixture, Config, MonkeyPatch, fixture, mark, param
from shutil          import copyfile
from subprocess      import run
from sys             import executable
from types           import ModuleType

BASE = {
    ".mise/bin/pytest"    : "",
    ".mise/tasks/py/test" : "",
    "pyproject.toml"      : (
        '"--snapshot-default-extension=common.snapshots.PlainFile"\n'
        '"-p common.agents_pool"\n'
    ),
    "src/squirtl/agent/memory.py"          : "",
    "src/squirtl/cli/__init__.py"          : "",
    "src/squirtl/docs/references.bib"      : "@misc{sutton2018}\n",
    "tests/py/agent/conftest.py"           : '"docs/notes/readme.md"\n',
    "tests/py/agent/fixtures/memory/a.txt" : "from common.agents import each_agent\n",
    "tests/py/agent/learner.py"            : "from common.agents import each_agent\n",
    "tests/py/agent/memory.py"             : "def test_remembers(event):\n    pass\n",
    "tests/py/agent/networks.py"           : "import common.records as records\n",
    "tests/py/cli/app.py"           : "",
    "tests/py/cli/conftest.py"      : "from common.cli import Invoker\n",
    "tests/py/common/agents.py"     :
        '"docs/notes/license.md"\n"src/squirtl/search/tiles.bin"\n',
    "tests/py/common/cli.py"        : "from common.records import idled\n",
    "tests/py/common/console.py"    : "",
    "tests/py/common/evaluation.py" : '"docs/notes/citation.cff"\n',
    "tests/py/common/records.py"    : "from common.cli import Invoker\n",
    "tests/py/common/snapshots.py"  : "",
    "tests/py/conftest.py"          : (
        "from pytest import fixture\n\nfrom common.console import set_event\n\n\n"
        "@fixture\ndef event():\n    return set_event\n\n\n"
        '"docs/notes/setup.md"\n'
    ),
    "tests/py/evaluation/scores.py" : "from squirtl.agent.memory import Memory\n",
    "tests/py/repo/checks.py"       :
        '"src/squirtl/docs/references.bib"\n"src/squirtl/agent/layout.toml"\n',
    "tests/py/runs/trainer.py"      :
        "def test_trains():\n    from common.agents import each_agent\n",
    "tests/py/search/tree.py"       : "from common.agents_pool import each_pool\n",
    "tests/py/tasks/bin.py"         : "",
    "tests/py/tasks/py.py"          : ""
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
    "pyproject.toml"              :
        '"-p common.plugin"\ntemplate = "squirtl.startup.imports:start"\n',
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
    "src/squirtl/startup/eager.py"   : "",

    "src/squirtl/startup/imports.py":
        "from squirtl.startup.eager import EAGER\n\n\ndef start():\n    pass\n",

    "tests/py/cli/watch.py"      : "import squirtl.emulator.console as console\n",
    "tests/py/common/console.py" : "from squirtl.emulator.console import GameBoy\n",
    "tests/py/common/plugin.py"  : "from common.terms import each_term\n",
    "tests/py/common/terms.py"   : "from squirtl.reward import Term\n",
    "tests/py/conftest.py"       : CONFTEST,
    "tests/py/docs/commands.py"  : "from squirtl.cli import app\n",

    "tests/py/docs/listed.py": (
        "import pkgutil\nimport squirtl.docs as listed\n\n"
        "NAMES = [*pkgutil.walk_packages(listed.__path__)]\n"
    ),
    "tests/py/docs/outputs.py": (
        "from pkgutil import iter_modules\n\nfrom squirtl import docs\n\n"
        "NAMES = [module.name for module in iter_modules(docs.__path__)]\n"
    ),

    "tests/py/docs/paths.py": "from squirtl import docs\n\nPATHS = [*docs.__path__]\n",

    "tests/py/docs/stdlib.py": (
        "import email\nfrom pkgutil import iter_modules\n\nfrom squirtl import docs\n\n"
        "NAMES = [docs, *iter_modules(email.__path__)]\n"
    ),
    "tests/py/emulator/console.py" : "from squirtl.emulator import console\n",
    "tests/py/reward/conftest.py"  : "from squirtl.emulator.console import GameBoy\n",
    "tests/py/reward/progress.py"  : "import os\n",
    "tests/py/runs/fixtures/handover/a.py": "import squirtl.emulator.console\n",

    "tests/py/runs/handover.py": """
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

    "tests/py/runs/marked.py": (
        'from pytest import mark\n\npytestmark = mark.usefixtures("limited")\n\n\n'
        "async def test_waits():\n    pass\n"
    ),

    "tests/py/runs/nulled.py": (
        "from pytest import fixture\n\n\n@fixture(autouse=True)\ndef nulled(null):\n"
        "    pass\n\n\ndef test_nulls():\n    pass\n"
    ),

    "tests/py/runs/trainer.py" : "from squirtl.runs.trainer import train\n",
    "tests/py/search/tree.py"  : "from common.console import set_event\n",

    "tests/py/search/workers.py":
        '"squirtl.emulator.console.GameBoy.press"\n"squirtl.unknown.name"\n',

    "tests/py/startup/imports.py":
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
            ["format", "--diff", ".mise/tasks", "src", "tests/py"],
            id = "format"
        ),
        param(
            "lint",
            {},
            [
                "check", "--output-format", "text", "--diff",
                ".mise/tasks", "src", "tests/py"
            ],
            id = "lint-local"
        ),
        param(
            "lint",
            {"GITHUB_ACTIONS": "true"},
            [
                "check", "--output-format", "github", "--diff",
                ".mise/tasks", "src", "tests/py"
            ],
            id = "lint-actions"
        ),
        param("snapshots", {}, ["-p", "common.skipped", "--diff"], id="snapshots"),
        param(
            "split",
            {},
            ["--cov", "--cov-fail-under=0", "--cov-report=", "--diff"],
            id = "split"
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
        param(".mise/bin/pytest", ["tests/py/tasks/bin.py"], id="wrapper"),
        param(".mise/tasks/py/lint", ["tests/py/tasks/py.py"], id="task"),
        param(
            "src/squirtl/docs/references.bib",
            ["tests/py/repo/checks.py"],
            id = "named"
        ),
        param("pyproject.toml", ["tests/py"], id="manifest"),
        param(
            "src/squirtl/agent/memory.py",
            ["tests/py/agent/memory.py", "tests/py/evaluation/scores.py"],
            id = "module"
        ),
        param("src/squirtl/cli/__init__.py", ["tests/py/cli/app.py"], id="app"),
        param(
            "src/squirtl/agent/layout.toml",
            ["tests/py/agent", "tests/py/repo/checks.py"],
            id = "package-file"
        ),
        param("tests/py/agent/conftest.py", ["tests/py/agent"], id="conftest"),
        param(
            "src/squirtl/search/tiles.bin",
            [
                "tests/py/agent/learner.py", "tests/py/runs/trainer.py",
                "tests/py/search"
            ],
            id = "package-file-helper-named"
        ),
        param("docs/notes/readme.md", ["tests/py/agent"], id="conftest-named"),
        param("docs/notes/setup.md", ["tests/py"], id="root-conftest-named"),
        param(
            "tests/py/agent/fixtures/memory/a.txt",
            ["tests/py/agent/memory.py"],
            id = "snapshot"
        ),
        param("tests/py/agent/memory.py", ["tests/py/agent/memory.py"], id="test"),
        param(
            "tests/py/common/agents.py",
            ["tests/py/agent/learner.py", "tests/py/runs/trainer.py"],
            id = "helper"
        ),
        param(
            "docs/notes/license.md",
            ["tests/py/agent/learner.py", "tests/py/runs/trainer.py"],
            id = "helper-named"
        ),
        param(
            "tests/py/common/cli.py",
            ["tests/py/agent/networks.py", "tests/py/cli"],
            id = "conftest-helper"
        ),
        param(
            "tests/py/common/console.py",
            ["tests/py/agent/memory.py::test_remembers"],
            id = "root-conftest-helper"
        ),
        param(
            "tests/py/common/records.py",
            ["tests/py/agent/networks.py", "tests/py/cli"],
            id = "helper-helper"
        ),
        param("tests/py/common/snapshots.py", ["tests/py"], id="manifest-helper"),
        param("tests/py/conftest.py", ["tests/py"], id="root-conftest")
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

    assert printed("py/affected") == ["tests/py/repo/checks.py"]


@mark.parametrize(
    "first",
    [
        param("docs/glossary.md", id="unnamed"),
        param("tests/py/common/search.py", id="unimported-helper")
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
    branch(True, "tests/py/repo/checks.py")

    assert printed("py/affected") == ["tests/py/repo/checks.py"]


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
        param("tests/py/common/search.py", id="unimported-helper"),
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
    function rewriting `tests/py/conftest.py` past it before returning what
    the `py:affected` reader selects for the changed paths it receives.

    Returns:
        A function taking the conftest's text in the working tree and then
        the changed paths, which returns the reader's selection, or
        `["tests/py"]` where a change reaches every test.
    """
    checkout(SUITE)
    git("init", "--quiet")
    git("add", "--all")
    git("commit", "--message", "Base", "--quiet")

    def select(conftest: str, *changed: str) -> list[str]:
        """
        Writes `conftest` as `tests/py/conftest.py` and reads the selection.
        """
        checkout({"tests/py/conftest.py": conftest})
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
                "tests/py/cli/watch.py", "tests/py/emulator/console.py",
                "tests/py/reward", "tests/py/runs/handover.py::test_plays",
                "tests/py/search/tree.py", "tests/py/search/workers.py",
                "tests/py/startup/imports.py"
            ],
            id = "module"
        ),
        param(
            "src/squirtl/emulator/schemas.py",
            ["tests/py/runs/handover.py::test_patches", "tests/py/startup/imports.py"],
            id = "quoted-in-root-fixture"
        ),
        param(
            "src/squirtl/runs/seeds.py",
            ["tests/py/runs/trainer.py", "tests/py/startup/imports.py"],
            id = "loaded-through-a-function-local-import-and-a-cycle"
        ),
        param(
            "src/squirtl/docs/regions.py",
            [
                "tests/py/docs/listed.py", "tests/py/docs/outputs.py",
                "tests/py/startup/imports.py"
            ],
            id = "under-a-walked-package"
        ),
        param("src/squirtl/reward/terms.py", ["tests/py"], id="reexported-to-plugin"),
        param("tests/py/common/terms.py", ["tests/py"], id="plugin-helper"),
        param("tests/py/common/removed.py", ["tests/py"], id="removed"),
        param("src/squirtl/search/tree.py", ["tests/py"], id="read-by-autouse"),
        param(
            "src/squirtl/search/__init__.py",
            ["tests/py"],
            id = "package-of-root-import"
        ),
        param("src/squirtl/startup/imports.py", ["tests/py"], id="start-file-module"),
        param("src/squirtl/startup/eager.py", ["tests/py"], id="loaded-by-start-file"),
        param(
            "tests/py/common/console.py",
            ["tests/py/search/tree.py"],
            id = "helper-unread-by-root-fixtures"
        ),
        param(
            "src/squirtl/cli/train.py",
            ["tests/py/docs/commands.py", "tests/py/startup/imports.py"],
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
    of package modules, a function-local import and a cycle included,
    each test module walking a package holding it by computed name, the
    folder of a subpackage conftest importing it, and the tests requesting
    a root fixture reading a name the root conftest binds to it, while a
    removed file, a helper `pyproject.toml` loads as a plugin, a module the
    start-file callable `pyproject.toml` names loads, a name the autouse
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
                "tests/py/runs/handover.py::test_clones",
                "tests/py/runs/handover.py::test_clones_each",
                "tests/py/runs/handover.py::test_clones_listed"
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
            [
                "tests/py/runs/handover.py::test_names",
                "tests/py/runs/nulled.py::test_nulls"
            ],
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
            ["tests/py"],
            id = "autouse"
        ),
        param(
            '    Marks each test.\n    """\n',
            '    """\n    del items\n',
            ["tests/py"],
            id = "hook"
        ),
        param("LIMIT = 3", "LIMIT = 4", ["tests/py"], id="name-a-fixture-reads"),
        param(
            "LIMIT = 3",
            'LIMIT = 3\npytest_plugins = ["common.terms"]',
            ["tests/py"],
            id = "plugins"
        ),
        param(
            "\n\n@fixture\ndef null",
            "\n\nprint()\n\n\n@fixture\ndef null",
            ["tests/py"],
            id = "statement"
        ),
        param(
            "@fixture\ndef limited():",
            '@fixture(scope="session")\ndef limited():',
            [
                "tests/py/runs/handover.py::test_caps",
                "tests/py/runs/marked.py::test_waits"
            ],
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
    `tests/py/conftest.py`, the tests requesting a fixture whose definition
    the change touches or that reads a name an import line binds anew,
    none for a docstring or a binding no fixture reads, and every test for
    a change to the autouse fixture, a hook, `pytest_plugins`, a name a
    fixture reads, or any other statement.
    """
    assert old in CONFTEST

    assert reach(CONFTEST.replace(old, new), "tests/py/conftest.py") == selected


def test_combine_stops_on_a_part_it_cannot_read(
    load_task   : Callable[[str], ModuleType],
    monkeypatch : MonkeyPatch,
    tmp_path    : Path
):
    """
    Asserts that `py:combine` returns the failing status of the combine and
    writes no report where the one part it finds is a folder rather than
    a data file, even though a data file covering every line sits where a
    report would read.
    """
    source = tmp_path / "module.py"

    monkeypatch.chdir(tmp_path)
    source.write_text("a = 1\n")
    (tmp_path / "parts/1/data").mkdir(parents=True)

    recorded = CoverageData()
    recorded.add_lines({str(source): [1]})
    recorded.write()

    assert load_task(".mise/tasks/py/combine.py").combine(tmp_path / "parts") == 1
    assert not (tmp_path / "htmlcov").exists()


def test_reach_prints_each_selection_or_every_test(
    capsys    : CaptureFixture[str],
    load_task : Callable[[str], ModuleType],
    reach     : Callable[..., list[str]]
):
    """
    Pins that the `py:affected` reader prints one selection a line, nothing
    where no test is reached, and `tests/py` alone once a change reaches
    every test.
    """
    module = load_task(".mise/tasks/py/reach.py")

    module.main("HEAD")
    module.main("HEAD", "tests/py/common/console.py")
    module.main("HEAD", "tests/py/common/terms.py")

    assert capsys.readouterr().out == "tests/py/search/tree.py\ntests/py\n"


def test_reach_selects_every_test_where_the_root_conftest_walks_a_changed_module(
    reach: Callable[..., list[str]]
):
    """
    Pins that the `py:affected` reader selects every test where
    `tests/py/conftest.py` walks the package holding a changed module
    through `pkgutil.walk_packages`, since no fixture is bound to what it
    loads.
    """
    assert reach(
        CONFTEST + "\n\nfrom pkgutil import walk_packages\n\nimport squirtl\n"
        "\nNAMES = [*walk_packages(squirtl.__path__)]\n",
        "src/squirtl/docs/regions.py"
    ) == ["tests/py"]


@mark.parametrize(
    ("files", "status", "percent"),
    [
        param({"parts/1/data": [1, 2], "parts/2/data": [3, 4]}, 0, 100, id="combined"),
        param({"parts/1/data": [1, 2], "parts/2/data": [3]}, 2, 75, id="below"),
        param({"data": [1, 2, 3, 4]}, 0, 100, id="local")
    ]
)
def test_combine_reports_the_combined_data_and_gates_its_total(
    capsys       : CaptureFixture[str],
    files        : dict[str, list[int]],
    load_task    : Callable[[str], ModuleType],
    monkeypatch  : MonkeyPatch,
    percent      : int,
    pytestconfig : Config,
    status       : int,
    tmp_path     : Path
):
    """
    Pins that `py:combine` combines every machine's data file under
    `.cache/coverage/parts/` before it writes the HTML report, the JSON
    report, and the terminal table and gates the total, so the lines each
    machine ran add up, exits 2 where the combined total falls below the
    `fail_under` that `pyproject.toml` sets, and reports on the data file a
    local run wrote where no part exists.
    """
    source = tmp_path / "src/squirtl/module.py"
    data   = tmp_path / ".cache/coverage"

    monkeypatch.chdir(tmp_path)
    source.parent.mkdir(parents=True)
    source.write_text("a = 1\nb = 2\nc = 3\nd = 4\n")
    copyfile(pytestconfig.rootpath / "pyproject.toml", tmp_path / "pyproject.toml")

    for name, lines in files.items():
        (data / name).parent.mkdir(exist_ok=True, parents=True)
        recorded = CoverageData(basename=str(data / name))
        recorded.add_lines({str(source): lines})
        recorded.write()

    assert load_task(".mise/tasks/py/combine.py").combine(data / "parts") == status
    assert (data / "html/index.html").is_file()
    assert "TOTAL" in capsys.readouterr().out
    assert loads(
        (data / "coverage.json").read_text()
    )["totals"]["percent_covered"] == percent


@mark.parametrize(
    ("snapshots", "returncode"),
    [
        param(["test_kept"], 0, id="borne"),
        param(["test_gone", "test_kept"], 1, id="unborne")
    ]
)
def test_snapshots_fails_on_a_snapshot_no_collected_test_bears(
    pytestconfig : Config,
    returncode   : int,
    snapshots    : list[str],
    tmp_path     : Path
):
    """
    Pins that the plugin `py:snapshots` loads skips every collected test
    while syrupy still fails the run on a snapshot whose name no collected
    test bears, and keeps the snapshot of a test it skipped.
    """
    fixtures = tmp_path / "fixtures/test_sample"

    fixtures.mkdir(parents=True)
    (tmp_path / "test_sample.py").write_text(
        "def test_kept(snapshot):\n    assert snapshot == 'kept'\n"
    )

    for name in snapshots:
        (fixtures / f"{name}.txt").write_text("kept")

    # The bare `env` drops `PYTEST_XDIST_WORKER`, under which syrupy skips its report.
    finished = run(
        [
            executable, "-m", "pytest", "-p", "common.skipped", "--rootdir",
            str(tmp_path),
            "--snapshot-default-extension=common.snapshots.PlainFile",
            "--snapshot-dirname=fixtures"
        ],
        capture_output = True,
        cwd            = tmp_path,
        env            = {"PYTHONPATH": str(pytestconfig.rootpath / "tests/py")},
        text           = True
    )

    assert (finished.returncode, "1 skipped" in finished.stdout) == (returncode, True)


def test_reach_selects_the_tests_requesting_a_removed_root_fixture(
    reach: Callable[..., list[str]]
):
    """
    Pins that the `py:affected` reader selects the tests still requesting
    a fixture `tests/py/conftest.py` no longer defines, through the side of
    the change that defined it, leaving out a test whose class overrides it.
    """
    github, limited = (CONFTEST.index(f"@fixture\ndef {name}") for name in (
        "github", "limited"
    ))

    assert reach(
        CONFTEST[:github] + CONFTEST[limited:],
        "tests/py/conftest.py"
    ) == [
        "tests/py/runs/handover.py::test_clones",
        "tests/py/runs/handover.py::test_clones_each",
        "tests/py/runs/handover.py::test_clones_listed"
    ]
