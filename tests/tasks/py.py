"""
Pins the arguments each `py` task hands the program it runs, meaning the
output format `py:lint` chooses for the shell it runs in, the coverage flags
`py:coverage` passes pytest, the test modules `py:affected` selects from the
files a branch changes, each further argument forwarded after the flags and
ahead of the operands, and the folders `py:lint` and `py:format` name as the
formatter's operands.

The stand-in under `fixtures/` answers for `prose` and `pytest`, printing
each argument it receives on a line of its own, so no case starts either
program.
"""

from collections.abc import Callable, Mapping
from pathlib         import Path
from pytest          import fixture, mark, param

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
    "tests/agent/conftest.py"           : '".github/README.md"\n',
    "tests/agent/fixtures/memory/a.txt" : "from common.agents import each_agent\n",
    "tests/agent/learner.py"            : "from common.agents import each_agent\n",
    "tests/agent/memory.py"             : "",
    "tests/agent/networks.py"           : "import common.records as records\n",
    "tests/cli/app.py"           : "",
    "tests/cli/conftest.py"      : "from common.cli import Invoker\n",
    "tests/common/agents.py"     : '"LICENSE.md"\n',
    "tests/common/cli.py"        : "from common.records import idled\n",
    "tests/common/console.py"    : "",
    "tests/common/evaluation.py" : '"CITATION.cff"\n',
    "tests/common/records.py"    : "from common.cli import Invoker\n",
    "tests/common/snapshots.py"  : "",
    "tests/conftest.py"          : "from common.console import set_event\n",
    "tests/repo/checks.py"       :
        '"src/squirtl/docs/references.bib"\n"src/squirtl/agent/layout.toml"\n',
    "tests/runs/trainer.py"      : "    from common.agents   import each_agent\n",
    "tests/search/tree.py"       : "from common.agents_pool import each_pool\n",
    "tests/tasks/bin.py"         : "",
    "tests/tasks/py.py"          : ""
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
        param("src/squirtl/agent/memory.py", ["tests/agent/memory.py"], id="module"),
        param("src/squirtl/cli/__init__.py", ["tests/cli/app.py"], id="app"),
        param(
            "src/squirtl/agent/layout.toml",
            ["tests/agent", "tests/repo/checks.py"],
            id = "package-file"
        ),
        param("tests/agent/conftest.py", ["tests/agent"], id="conftest"),
        param(".github/README.md", ["tests/agent"], id="conftest-named"),
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
            "LICENSE.md",
            ["tests/agent/learner.py", "tests/runs/trainer.py"],
            id = "helper-named"
        ),
        param(
            "tests/common/cli.py",
            ["tests/agent/networks.py", "tests/cli"],
            id = "conftest-helper"
        ),
        param("tests/common/console.py", ["tests"], id="root-conftest-helper"),
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
    Pins the test modules `py:affected` hands pytest for one file changed
    since the merge base with `origin/main`, whether committed, modified, or
    untracked, after the arguments it forwards.
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
        param("CITATION.cff", id="unimported-helper-named")
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
