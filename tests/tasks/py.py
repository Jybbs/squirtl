"""
Pins the arguments the `py:check` and `py:format` tasks hand the
formatter and the `py:coverage` task hands pytest, meaning the output
format `py:check` chooses for the shell it runs in, the coverage flags
`py:coverage` passes, each further argument forwarded after the flags and
ahead of the operands, and the folders `.mise/lib/py.sh` names as those
operands.

The stand-in under `fixtures/` answers for `prose` and `pytest`, printing
each argument it receives on a line of its own, so no case starts either
program.
"""

from collections.abc import Callable
from pathlib         import Path
from pytest          import Config, MonkeyPatch, fixture, mark
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
    ("shell", "output"),
    [({}, "text"), ({"GITHUB_ACTIONS": "true"}, "github")],
    ids = ["local", "actions"]
)
def test_check_reports_in_the_format_its_shell_reads(
    monkeypatch : MonkeyPatch,
    output      : str,
    printed     : Callable[[str], list[str]],
    shell       : dict[str, str]
):
    """
    Pins that `py:check` asks the formatter for annotations under GitHub
    Actions and for text elsewhere, forwarding `--diff` ahead of the folders
    it checks.
    """
    for name, value in shell.items():
        monkeypatch.setenv(name, value)

    assert printed("check") == [
        "check", "--output-format", output, "--diff", ".mise/tasks", "src", "tests"
    ]


def test_coverage_runs_pytest_under_the_gate_ahead_of_its_arguments(
    printed: Callable[[str], list[str]]
):
    """
    Pins that `py:coverage` hands pytest `--cov`, which measures the run
    against `fail_under`, and the HTML and terminal reports, with `--diff`
    forwarded after them.
    """
    assert printed("coverage") == [
        "--cov", "--cov-report", "html", "--cov-report", "term", "--diff"
    ]


def test_format_forwards_its_arguments_ahead_of_the_folders(
    printed: Callable[[str], list[str]]
):
    """
    Pins that `py:format` hands the formatter `--diff` ahead of the folders
    it rewrites.
    """
    assert printed("format") == ["format", "--diff", ".mise/tasks", "src", "tests"]
