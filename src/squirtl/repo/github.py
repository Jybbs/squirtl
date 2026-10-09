"""
Defines what the `repo:labels` and `repo:rulesets` tasks send GitHub,
meaning `Command`, one `gh` command beside the JSON body it sends on
standard input, and `Plan`, the commands a task sends once its reader
confirms them.
"""

from collections.abc import Iterable
from http            import HTTPMethod
from json            import dumps
from pydantic        import BaseModel, JsonValue
from shlex           import join, quote
from subprocess      import check_output
from typing          import Self


class Command(BaseModel, extra="forbid", frozen=True, use_attribute_docstrings=True):
    """
    One `gh` command beside the JSON body it sends on standard input, acting
    on the repository `gh` resolves, which is the one `GH_REPO` names where
    that variable is set and the one the clone's remote names otherwise.
    """

    arguments: tuple[str, ...]
    """
    The arguments `gh` receives, in the order it receives them.
    """

    body: JsonValue = None
    """
    The JSON the command sends on standard input, or `None` where it sends
    nothing.
    """

    @property
    def argv(self) -> list[str]:
        """
        Spells the command out, asking `gh` to read the body from standard
        input where the command sends one.
        """
        return ["gh", *self.arguments, *(["--input", "-"] if self.stdin else [])]

    @property
    def line(self) -> str:
        """
        Spells the command as one shell line, feeding the body through a
        here-string, so pasting the line into a shell sends what `output`
        sends.
        """
        return join(self.argv) + (f" <<< {quote(self.stdin)}" if self.stdin else "")

    @property
    def stdin(self) -> str | None:
        """
        Writes the body as JSON, keeping each character outside ASCII as it
        is, or nothing where the command sends no body.
        """
        return None if self.body is None else dumps(self.body, ensure_ascii=False)

    @classmethod
    def api(
        cls,
        path   : str,
        *flags : str,
        body   : JsonValue  = None,
        method : HTTPMethod = HTTPMethod.GET
    ) -> Self:
        """
        Builds a call to GitHub's REST API at `path` under the repository,
        or at the repository itself where `path` is empty, sent as `method`
        with `flags` after the address.
        """
        return cls(
            arguments = (
                "api",
                "/".join(filter(None, ["repos/{owner}/{repo}", path])),
                "--method", method,
                *flags
            ),
            body = body
        )

    def output(self) -> str:
        """
        Runs the command, leaving what it prints to standard error on the
        terminal.

        Returns:
            What it printed to standard output.

        Raises:
            CalledProcessError: Where `gh` exits nonzero.
        """
        return check_output(self.argv, encoding="utf-8", input=self.stdin)


class Plan(BaseModel, extra="forbid", frozen=True, use_attribute_docstrings=True):
    """
    The commands a task sends GitHub once its reader confirms them, beside
    each object GitHub carries that no file under `.github/` declares, which
    the task names and leaves as it is.
    """

    strays: tuple[str, ...] = ()
    """
    Each object GitHub carries that no file declares, named with its kind.
    """

    writes: tuple[Command, ...] = ()
    """
    The commands that change GitHub, in the order the task sends them.
    """

    def __add__(self, other: Plan) -> Self:
        """
        Joins `other` after this plan, its strays and its writes following
        this plan's own.
        """
        return type(self)(
            strays = self.strays + other.strays,
            writes = self.writes + other.writes
        )

    def apply(self) -> int:
        """
        Prints each stray and then each write as the shell line it sends,
        and sends the writes once the reader answers `y` or `yes`, in any
        case, to the prompt naming the repository `gh` resolves. A plan
        holding no write says that GitHub already matches and asks nothing.

        Returns:
            The exit status, which is 1 where the reader declines or standard
            input closes before an answer, and 0 otherwise.
        """
        if self.strays:
            print(
                "Left as they are, since no file under .github/ declares them:",
                *self.strays,
                sep = "\n  "
            )

        if not self.writes:
            print("GitHub already matches the files under .github/")
            return 0

        print(*(write.line for write in self.writes), sep="\n")
        repository = (
            Command.api("", "--jq", ".full_name")
                   .output()
                   .strip()
        )

        try:
            answer = input(
                f"Send the commands above to {repository}? [y/N] "
            )
        except EOFError:
            answer = ""

        if answer.strip().lower() not in {"y", "yes"}:
            print("Sent nothing")
            return 1

        for write in self.writes:
            write.output()

        print(f"Sent every command above to {repository}")
        return 0

    @classmethod
    def leaving(
        cls,
        *,
        declared : Iterable[str],
        kind     : str,
        live     : Iterable[str],
        writes   : Iterable[Command]
    ) -> Self:
        """
        Builds the plan that sends `writes` and names, in sorted order, each
        `live` name `declared` leaves out, written as `the <kind> <name>`.
        """
        return cls(
            strays = tuple(
                f"the {kind} {name}" for name in sorted(set(live) - set(declared))
            ),
            writes = tuple(writes)
        )
