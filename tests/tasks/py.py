"""
Pins the arguments each `py` task hands the program it runs, meaning the
output format `py:lint` chooses for the shell it runs in, the coverage flags
`py:coverage` passes pytest, each further argument forwarded after the flags
and ahead of the operands, and the folders `py:lint` and `py:format` name as
the formatter's operands.

The stand-in under `fixtures/` answers for `prose` and `pytest`, printing
each argument it receives on a line of its own, so no case starts either
program.
"""

from collections.abc import Callable
from pathlib         import Path
from pytest          import fixture, mark, param


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
            ["--cov", "--cov-report", "html", "--cov-report", "term", "--diff"],
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
