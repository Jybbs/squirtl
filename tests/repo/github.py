"""
Pins how `Command` spells and runs one `gh` command and how `Plan` applies
the commands a task sends, covering:

- The argument vector and the shell line of a command with a body and of
  one without
- The address `Command.api` builds for the repository and for a path under
  it
- The body a command sends on standard input and what it returns
- The answers on which a plan sends its writes, and what it prints first

The `fp` fixture pytest-subprocess provides answers every `gh` command, so
no case reaches GitHub.
"""

from collections.abc   import Callable
from http              import HTTPMethod
from pytest            import CaptureFixture, mark, param, raises
from pytest_subprocess import FakeProcess
from subprocess        import CalledProcessError

from squirtl.repo.github import Command, Plan


@mark.parametrize(
    ("command", "argv", "line"),
    [
        param(
            Command(arguments=("label", "list")),
            ["gh", "label", "list"],
            "gh label list",
            id = "no-body"
        ),
        param(
            Command.api("topics", body={"names": ["dqn"]}, method= HTTPMethod.PUT),
            [
                "gh", "api", "repos/{owner}/{repo}/topics", "--method",
                "PUT", "--input", "-"
            ],
            "gh api 'repos/{owner}/{repo}/topics' --method PUT --input - "
            '<<< \'{"names": ["dqn"]}\'',
            id = "body"
        ),
        param(
            Command.api(
                "rulesets",
                body   = {"context": "🎒 Brief"},
                method = HTTPMethod.POST
            ),
            [
                "gh", "api", "repos/{owner}/{repo}/rulesets", "--method",
                "POST", "--input", "-"
            ],
            "gh api 'repos/{owner}/{repo}/rulesets' --method POST --input - "
            '<<< \'{"context": "🎒 Brief"}\'',
            id = "body-outside-ascii"
        )
    ]
)
def test_a_command_reads_a_body_from_standard_input_only_where_it_sends_one(
    argv    : list[str],
    command : Command,
    line    : str
):
    """
    Pins that a command asks `gh` to read standard input only where it
    carries a body, and that its shell line feeds that body through a
    here-string, keeping each character outside ASCII as it is.
    """
    assert command.argv == argv
    assert command.line == line


@mark.parametrize(
    ("path", "address"),
    [
        param("", "repos/{owner}/{repo}", id="the-repository"),
        param(
            "actions/permissions",
            "repos/{owner}/{repo}/actions/permissions",
            id = "a-path"
        )
    ]
)
def test_api_addresses_the_repository_or_a_path_under_it(address: str, path: str):
    """
    Pins that `Command.api` addresses the repository itself for an empty
    path and the path under it otherwise, sending `GET` unless told
    otherwise and placing the flags after the method.
    """
    assert Command.api(path, "--paginate").arguments == (
        "api", address, "--method", "GET", "--paginate"
    )


def test_a_plan_holding_no_write_asks_nothing(
    capsys : CaptureFixture[str],
    fp     : FakeProcess
):
    """
    Pins that a plan holding strays and no write lists the strays, says
    GitHub already matches, and exits 0 without reading the repository's
    name or raising a prompt.
    """
    assert Plan(strays=("the label 🔥 old",)).apply() == 0
    assert capsys.readouterr().out == (
        "Left as they are, since no file under .github/ declares them:\n"
        "  the label 🔥 old\n"
        "GitHub already matches the files under .github/\n"
    )
    assert list(fp.calls) == []


def test_a_plan_stops_at_the_first_write_github_refuses(
    answered : Callable[[str], None],
    fp       : FakeProcess
):
    """
    Pins that a plan the reader confirms raises at the first write `gh`
    exits nonzero on and sends none of the writes after it.
    """
    refused, later = (
        Command(arguments=("label", "create", "a")),
        Command(arguments=("label", "create", "b"))
    )

    answered("y\n")
    fp.register(refused.argv, returncode=1)
    fp.register(later.argv)

    with raises(CalledProcessError):
        Plan(writes=(refused, later)).apply()

    assert fp.call_count(later.argv) == 0


def test_adding_a_plan_appends_its_strays_and_its_writes():
    """
    Pins that adding a plan to another puts its strays and its writes after
    the first plan's own.
    """
    first, second = Command(arguments=("first",)), Command(arguments=("second",))

    assert Plan(strays=("a",), writes=(first,)) + Plan(
        strays = ("b",),
        writes = (second,)
    ) == Plan(strays=("a", "b"), writes=(first, second))


def test_output_raises_where_gh_exits_nonzero(fp: FakeProcess):
    """
    Pins that a command `gh` refuses raises `CalledProcessError` rather
    than returning.
    """
    fp.register(["gh", "label", "list"], returncode=1)

    with raises(CalledProcessError):
        Command(arguments=("label", "list")).output()


def test_output_sends_the_body_and_returns_what_gh_printed(fp: FakeProcess):
    """
    Pins that a command sends its body to `gh` as JSON on standard input and
    returns what `gh` printed to standard output.
    """
    command = Command.api("topics", body={"names": ["dqn"]}, method= HTTPMethod.PUT)
    sent    = []

    fp.register(command.argv, stdin_callable=sent.append, stdout="printed\n")

    assert command.output() == "printed\n"
    assert sent == ['{"names": ["dqn"]}']


@mark.parametrize(
    ("reply", "code", "closing"),
    [
        param("y\n", 0, "Sent every command above to Jybbs/squirtl\n", id="y"),
        param("Yes\n", 0, "Sent every command above to Jybbs/squirtl\n", id="yes"),
        param("n\n", 1, "Sent nothing\n", id="n"),
        param("\n", 1, "Sent nothing\n", id="empty"),
        param("", 1, "Sent nothing\n", id="closed")
    ]
)
def test_a_plan_sends_its_writes_only_once_the_reader_answers_yes(
    answered : Callable[[str], None],
    capsys   : CaptureFixture[str],
    closing  : str,
    code     : int,
    fp       : FakeProcess,
    reply    : str
):
    """
    Pins that a plan prints its strays and then each write as its shell line
    ahead of the prompt naming the repository, sends the writes in order
    only where the reader answers `y` or `yes` in any case, and otherwise
    exits 1 having sent nothing, a closed standard input counting as a
    refusal.
    """
    writes = (
        Command(arguments=("label", "create", "a")),
        Command(arguments=("label", "create", "b"))
    )

    answered(reply)
    for write in writes:
        fp.register(write.argv)

    assert Plan(strays=("the label wontfix",), writes=writes).apply() == code
    assert capsys.readouterr().out == (
        "Left as they are, since no file under .github/ declares them:\n"
        "  the label wontfix\n"
        "gh label create a\ngh label create b\n"
        "Send the commands above to Jybbs/squirtl? [y/N] " + closing
    )
    assert [call for call in fp.calls if call[1] == "label"] == (
        [write.argv for write in writes] if code == 0 else []
    )
