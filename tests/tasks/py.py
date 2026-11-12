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
    ".mise/bin/pytest"            : "",
    ".mise/tasks/py/test"         : "",
    "docs/references.bib"         : "@misc{sutton2018}\n",
    "pyproject.toml"              : "",
    "src/squirtl/agent/memory.py" : "",
    "tests/agent/conftest.py"     : "",
    "tests/agent/fixtures/memory/a.txt" : "",
    "tests/agent/memory.py"             : "",
    "tests/common/cli.py"               : "",
    "tests/conftest.py"                 : "",
    "tests/repo/checks.py"              : '"docs/references.bib"\n',
    "tests/tasks/bin.py"                : "",
    "tests/tasks/py.py"                 : ""
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
        param("docs/references.bib", ["tests/repo/checks.py"], id="named"),
        param("pyproject.toml", ["tests"], id="manifest"),
        param("src/squirtl/agent/memory.py", ["tests/agent/memory.py"], id="module"),
        param("tests/agent/conftest.py", ["tests/agent"], id="conftest"),
        param(
            "tests/agent/fixtures/memory/a.txt",
            ["tests/agent/memory.py"],
            id = "snapshot"
        ),
        param("tests/agent/memory.py", ["tests/agent/memory.py"], id="test"),
        param("tests/common/cli.py", ["tests"], id="helper"),
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
    git("mv", "docs/references.bib", "docs/sources.bib")
    git("commit", "--message", "Rename")

    assert printed("py/affected") == ["tests/repo/checks.py"]


@mark.parametrize(
    "path",
    [param(None, id="unchanged"), param("src/squirtl/agent/replay.py", id="unmirrored")]
)
def test_affected_starts_no_pytest_where_no_test_module_is_reached(
    branch  : Callable[[bool, str], None],
    path    : str | None,
    printed : Callable[..., list[str]]
):
    """
    Pins that `py:affected` names the merge base and starts no pytest on a
    branch changing no file, and on one whose one changed file is a module
    with no mirrored test module, since pytest given no path runs the whole
    suite.
    """
    if path:
        branch(False, path)

    [line] = printed("py/affected")

    assert line.startswith("No test module reaches a file changed since ")
