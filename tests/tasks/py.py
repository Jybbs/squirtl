"""
Pins the arguments each `py` task hands the program it runs, meaning the
output format `py:check` chooses for the shell it runs in, the coverage
flags `py:coverage` passes pytest, each further argument forwarded after the
flags and ahead of the operands, and the folders `.mise/lib/py.sh` names as
the formatter's operands.

The stand-in under `fixtures/` answers for `prose` and `pytest`, printing
each argument it receives on a line of its own, so no case starts either
program.
"""

from collections.abc import Callable
from pathlib         import Path
from pytest          import Config, MonkeyPatch, fixture, mark, param
from subprocess      import run


@fixture(autouse=True)
def stand_in(
    install_stand_ins : Callable[..., Path],
    monkeypatch       : MonkeyPatch,
    pytestconfig      : Config
):
    """
    Puts the stand-in ahead of the real `prose` and `pytest` on the path
    for every case and sets the `MISE_PROJECT_ROOT` that `py:check` and
    `py:format` source `.mise/lib/py.sh` through.
    """
    install_stand_ins("echo.sh", "prose", "pytest")
    monkeypatch.setenv("MISE_PROJECT_ROOT", str(pytestconfig.rootpath))


@fixture
def printed(pytestconfig: Config) -> Callable[[str], list[str]]:
    """
    Builds a runner of the task named under `.mise/tasks/py/` with `--diff`,
    which reads back each argument the stand-in received.
    """
    tasks = pytestconfig.rootpath / ".mise/tasks/py"

    return lambda task: run(
        [tasks / task, "--diff"],
        capture_output = True,
        check          = True,
        text           = True
    ).stdout.splitlines()


@mark.parametrize(
    ("task", "shell", "argv"),
    [
        param(
            "check",
            {},
            [
                "check", "--output-format", "text", "--diff",
                ".mise/tasks", "src", "tests"
            ],
            id = "check-local"
        ),
        param(
            "check",
            {"GITHUB_ACTIONS": "true"},
            [
                "check", "--output-format", "github", "--diff",
                ".mise/tasks", "src", "tests"
            ],
            id = "check-actions"
        ),
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
        param("test", {}, ["--diff"], id="test")
    ],
    indirect = ["shell"]
)
def test_each_task_hands_its_program_its_flags_and_arguments(
    argv    : list[str],
    printed : Callable[[str], list[str]],
    shell   : dict[str, str],
    task    : str
):
    """
    Pins the argument list each `py` task hands its program, with `py:check`
    asking the formatter for annotations under GitHub Actions and for text
    elsewhere, and every task forwarding `--diff` after its own flags and
    ahead of any folders the formatter reads.
    """
    assert printed(task) == argv
