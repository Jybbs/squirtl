"""
Defines the records the `repo` tasks read from the files of the checkout,
each a `Record`, where a registry's record refuses a key no field declares,
so a misspelled key fails the read before anything is sent, whereas a
record of what GitHub, mise, or a manifest returns ignores the keys it does
not read:

- `JsonFile`, `TomlFile`, and `YamlFile`, the bases of a record one file holds,
  `StepFile`, the base of a YAML file whose steps run scripts, and
  `Endpoint`, the base of a table sent whole as the body of a `PUT`
- The registries under `.github/` and `Project`, each registry deriving the
  `Plan` that brings GitHub in line with it
- `Finding`, one divergence `repo:audit` reports, and `Unreadable`, raised
  where a file the audit reads fails to parse
- The records of every other file the audit reads, among them `Manifest`,
  `Workflow`, `Script`, and the `Tree` and `Tasks` that git and mise list
"""

from abc             import ABC, abstractmethod
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from contextlib      import contextmanager
from enum            import StrEnum, auto
from fnmatch         import fnmatch
from functools       import cached_property
from http            import HTTPMethod
from itertools       import chain, groupby, takewhile
from json            import load
from packaging.requirements import Requirement
from packaging.specifiers   import SpecifierSet
from packaging.utils        import canonicalize_name
from packaging.version      import Version
from pathlib                import Path
from pydantic            import (
    AliasPath, BeforeValidator, Field, HttpUrl, InstanceOf, JsonValue,
    StringConstraints, TypeAdapter, ValidationError
)
from re         import escape, finditer, fullmatch, search, sub
from shlex      import shlex, split
from stat       import S_IXUSR
from subprocess import SubprocessError, check_output, run
from tomllib    import loads
from typing     import Annotated, Any, ClassVar, Literal, Self
from yaml                import (
    DocumentEndEvent, MappingNode, Node, NodeEvent, SafeLoader, SequenceNode,
    YAMLError, compose_all, parse
)

from squirtl.emulator.schemas import Record
from squirtl.repo.github      import Command, Plan

type Lines = Annotated[
    dict[int, tuple[str, ...]],
    BeforeValidator(
        lambda script: command_lines(script) if isinstance(script, str) else {}
    )
]
type Pin           = Annotated[InstanceOf[Requirement], BeforeValidator(Requirement)]
type Specifiers    = Annotated[InstanceOf[SpecifierSet], BeforeValidator(SpecifierSet)]
type VersionNumber = Annotated[InstanceOf[Version], BeforeValidator(Version)]


def command_lines(text: str) -> dict[int, tuple[str, ...]]:
    """
    Splits the shell script `text` into the words of each command line,
    keyed by the line it opens on counting from 1, joining a line that ends
    in a backslash to the next and leaving out comments and blank lines.
    Each line splits as `shell_words` splits it.

    Raises:
        ValueError: Where a quote opens and never closes.
    """
    lines   = {}
    opening = None
    pending = ""

    for number, line in enumerate(text.splitlines(), start=1):
        opening = opening or number

        if line.endswith("\\"):
            pending += line.removesuffix("\\") + " "
            continue

        if words := tuple(shell_words(pending + line)):
            lines[opening] = words

        opening, pending = None, ""

    return lines


def following(command: tuple[str, ...], words: Sequence[str]) -> list[tuple[str, ...]]:
    """
    Lists the words after each place the words of `command` stand in order
    among `words`, so a line that runs `uv run` twice yields what each run
    takes.
    """
    size = len(command)

    return [
        tuple(words[index + size:])
        for index in range(len(words))
        if tuple(words[index:index + size]) == command
    ]


def shell_words(text: str) -> Iterator[str]:
    """
    Splits one shell command line into its words, each of `;`, `&&`, `|`,
    `(`, and the like standing as a word of its own, and follows each word
    holding a `$(` with the words of the command inside it, up to the `)`
    closing it, so a command inside a quoted substitution, which stays one
    word, starts on a word of its own too.

    Raises:
        ValueError: Where a quote opens and never closes.
    """
    lexer = shlex(text, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True

    for word in lexer:
        yield word

        if "$(" in word:
            depth = 1

            for inner in shell_words(word.partition("$(")[2]):
                if not inner.strip("();<>|&"):
                    depth += inner.count("(") - inner.count(")")

                if depth < 1:
                    break

                yield inner


def admits(file: Path, pattern: str) -> bool:
    """
    Tells whether the GitHub Actions path filter `pattern` matches `file`,
    reading `*` as any run of characters but `/`, `**` as any run at all,
    `**/` as any number of whole directories, `?` and `+` as zero or one and
    one or more of the character before them, and `[]` as one character of a
    set, as GitHub's filter pattern cheat sheet sets out.
    """
    regex = sub(
        r"\*\*/|\*\*|\*|[.^$(){}|\\]",
        lambda match: {"*": "[^/]*", "**": ".*", "**/": "(?:.*/)?"}.get(
            match[0],
            "\\" + match[0]
        ),
        pattern
    )

    return fullmatch(regex, file.as_posix()) is not None


class Author(Record, extra="ignore"):
    """
    One author `[project].authors` names.
    """

    name: str | None = None
    """
    The author's name, or `None` for an author named only by an address.
    """


class Block(Record):
    """
    One node of a YAML file PyYAML composes, read for its value and for the
    line it opens on. A mapping's keys keep the text they are written in, so
    `on`, which YAML 1.1 reads as `True`, stays `on`.
    """

    node: InstanceOf[Node]
    """
    The node PyYAML composed, an alias already resolved to the node its
    anchor names.
    """

    @property
    def line(self) -> int:
        """
        Numbers the line the node opens on, counting from 1.
        """
        return self.node.start_mark.line + 1

    @property
    def value(self) -> Any:
        """
        Builds the value the node holds, as `yaml.safe_load` builds it.
        """
        return SafeLoader("").construct_document(self.node)

    def at(self, *keys: str) -> Block | None:
        """
        Finds the block under each of `keys` in turn, or `None` where a key
        is missing or a block on the way holds no mapping.
        """
        block = self

        for key in keys:
            if (block := block.fields().get(key)) is None:
                return None

        return block

    def entries(self, *keys: str) -> list[Block]:
        """
        Wraps each item of the sequence under each of `keys` in turn, or
        nothing where a key is missing or the node there holds no sequence.
        """
        block = self.at(*keys)

        if block is None or not isinstance(block.node, SequenceNode):
            return []

        return [Block(node=item) for item in block.node.value]

    def fields(self, *keys: str) -> dict[str, Block]:
        """
        Wraps each value of the mapping under each of `keys` in turn, keyed
        by its key's text, or nothing where a key is missing or the node
        there holds no mapping.
        """
        block = self.at(*keys)

        if block is None or not isinstance(block.node, MappingNode):
            return {}

        return {key.value: Block(node=value) for key, value in block.node.value}

    def get(self, *keys: str, default: Any = None) -> Any:
        """
        Builds the value under each of `keys` in turn, or `default` where a
        key is missing or holds null.
        """
        value = None if (block := self.at(*keys)) is None else block.value

        return default if value is None else value


class Dependabot(Record):
    """
    The `[dependabot]` table, keyed by the endpoint each setting turns on
    through `PUT` or off through `DELETE`.
    """

    automated_security_fixes: bool = Field(alias="automated-security-fixes")
    """
    Whether Dependabot opens a pull request for each vulnerable dependency.
    """

    vulnerability_alerts: bool = Field(alias="vulnerability-alerts")
    """
    Whether Dependabot raises an alert for each vulnerable dependency.
    """

    @property
    def commands(self) -> tuple[Command, ...]:
        """
        Builds the command for each endpoint, a `PUT` turning on a setting
        that is true and a `DELETE` turning off one that is false, in the
        order the fields sit in.
        """
        return tuple(
            Command.api(
                endpoint,
                method = HTTPMethod.PUT if enabled else HTTPMethod.DELETE
            )
            for endpoint, enabled in self.model_dump(by_alias=True).items()
        )


class Endpoint(Record):
    """
    The base of a table sent whole as the body of the `PUT` to `path` under
    the repository.
    """

    path: ClassVar[str]

    @property
    def command(self) -> Command:
        """
        Builds the `PUT` that sends the table to `path`.
        """
        return Command.api(self.path, body=self.model_dump(), method=HTTPMethod.PUT)


class Feature(Record):
    """
    One feature `security_and_analysis` turns on or off.
    """

    status: Literal["disabled", "enabled"]
    """
    Whether the feature is on.
    """


class GithubRuleset(Record, extra="ignore"):
    """
    One ruleset GitHub's listing of the repository's rulesets returns, read
    for its id and its name.
    """

    id: int
    """
    The id an update addresses the ruleset by.
    """

    name: str
    """
    The name a file under `.github/rulesets/` matches the ruleset on.
    """


class JsonFile(Record):
    """
    The base of a record one JSON file holds whole, which `from_path`
    validates into the record.
    """

    file: ClassVar[Path]

    @classmethod
    def from_path(cls, path: Path) -> Self:
        """
        Reads the record the JSON file at `path` holds, raising `Unreadable`
        where the file fails to parse, on the line the parser names, or
        fails to validate.
        """
        with Finding.reading(path), path.open(encoding="utf-8") as file:
            return cls.model_validate(load(file))

    @classmethod
    def read(cls) -> Self:
        """
        Reads the record at `file`.
        """
        return cls.from_path(cls.file)


class Label(Record):
    """
    One row of the label registry.
    """

    color: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{6}$")]
    """
    The label's color, as six lowercase hexadecimal digits with no `#`.
    """

    description: Annotated[str, StringConstraints(max_length=100)]
    """
    What the label covers, in at most the 100 characters GitHub accepts.
    """

    name: str
    """
    The label's glyph, a space, and its word.
    """

    @property
    def command(self) -> Command:
        """
        Builds the `gh label create --force` command that creates the label
        or updates its color and description in place.
        """
        return Command(
            arguments = (
                "label", "create", "--color", self.color,
                "--description", self.description, "--force", self.name
            )
        )


class License(Record):
    """
    A license file `[project].license-files` names, read for its title and
    for the holders its copyright line names.
    """

    holders: str | None
    """
    Whom the copyright line names after its year, or `None` where the file
    carries no copyright line.
    """

    path: Path
    """
    The file, relative to the root of the checkout.
    """

    title: str
    """
    The file's first line, without the `#` a Markdown heading opens on.
    """

    @classmethod
    def from_path(cls, path: Path) -> Self:
        """
        Reads the license file at `path`, raising `Unreadable` where the
        file is missing or empty.
        """
        with Finding.reading(path):
            text      = path.read_text(encoding="utf-8")
            title, *_ = text.splitlines()
            match     = search(
                r"(?m)^Copyright (?:\(c\) )?[\d, -]+ (?P<holders>.+)$",
                text
            )

            return cls(
                holders = match and match["holders"],
                path    = path,
                title   = title.lstrip("# ")
            )


class LockedPackage(Record, extra="ignore"):
    """
    One package `uv.lock` resolves, read for its name and its version.
    """

    name: str
    """
    The package's name as the lockfile writes it.
    """

    version: VersionNumber | None = None
    """
    The version the lockfile resolves, or `None` for a package the
    lockfile resolves from a path with no version of its own.
    """


class Metadata(Record, extra="ignore"):
    """
    The `script` block of inline metadata a Python script declares, as PEP
    723 sets it out.
    """

    dependencies: list[Pin] = []
    """
    The packages the script runs on.
    """

    requires_python: Specifiers | None = Field(None, alias="requires-python")
    """
    The Python releases the script runs on, or `None` where it names none.
    """

    @classmethod
    def from_script(cls, text: str) -> Self | None:
        """
        Reads the `script` block of the inline metadata the script `text`
        carries, through the pattern PEP 723 gives for finding a block.

        Returns:
            The block, or `None` where `text` carries none.

        Raises:
            ValueError: Where `text` carries more than one `script` block.
        """
        blocks = [
            match["content"]
            for match in finditer(
                r"(?m)^# /// (?P<type>[a-zA-Z0-9-]+)$\s"
                r"(?P<content>(^#(| .*)$\s)+)^# ///$",
                text
            )
            if match["type"] == "script"
        ]

        if len(blocks) > 1:
            raise ValueError("the script carries more than one `script` block")

        if not blocks:
            return None

        return cls.model_validate(
            loads(
                "".join(
                    line.removeprefix("#").removeprefix(" ")
                    for line in blocks[0].splitlines(keepends=True)
                )
            )
        )


class Ruleset(JsonFile):
    """
    One ruleset a file under `.github/rulesets/` declares, as the body of
    the request that creates or updates it.
    """

    bypass_actors: list[dict[str, JsonValue]]
    """
    The actors the ruleset lets past its rules.
    """

    conditions: dict[str, JsonValue]
    """
    The refs the ruleset covers.
    """

    enforcement: Literal["active", "disabled", "evaluate"]
    """
    Whether GitHub enforces the rules, only reports them, or ignores them.
    """

    name: str
    """
    The name GitHub carries the ruleset under, which an update matches on.
    """

    rules: list[dict[str, JsonValue]]
    """
    The rules the ruleset enforces, each keyed by its `type`.
    """

    target: Literal["branch", "push", "tag"]
    """
    The kind of ref the ruleset covers.
    """

    @property
    def checks(self) -> list[str]:
        """
        Names each status check a `required_status_checks` rule of the
        ruleset requires.
        """
        return [
            check.get("context")
            for rule in self.rules
            if rule.get("type") == "required_status_checks"
            for check in rule.get("parameters", {}).get("required_status_checks", [])
        ]

    def command(self, live: Mapping[str, int]) -> Command:
        """
        Builds the `PUT` that updates in place the ruleset whose id `live`
        maps this one's name to, or the `POST` that creates this one where
        `live` holds no such name.
        """
        if (existing := live.get(self.name)) is None:
            return Command.api(
                "rulesets",
                body   = self.model_dump(),
                method = HTTPMethod.POST
            )

        return Command.api(
            f"rulesets/{existing}",
            body   = self.model_dump(),
            method = HTTPMethod.PUT
        )


class Severity(StrEnum):
    """
    How much a finding weighs, each member's value the name of the workflow
    command GitHub turns into an annotation of that weight.
    """

    ERROR   = auto()
    WARNING = auto()


class Repository(Record):
    """
    The `[repository]` table, the body of the request that updates the
    repository's features, merge settings, and security features.
    """

    allow_auto_merge: bool
    """
    Whether a pull request may merge itself once its checks pass.
    """

    allow_merge_commit: bool
    """
    Whether a pull request may merge through a merge commit.
    """

    allow_rebase_merge: bool
    """
    Whether a pull request may merge by rebasing its commits.
    """

    allow_squash_merge: bool
    """
    Whether a pull request may merge as one squashed commit.
    """

    allow_update_branch: bool
    """
    Whether a pull request offers to take in its base branch once it falls
    behind.
    """

    delete_branch_on_merge: bool
    """
    Whether a pull request's head branch is deleted once it merges.
    """

    has_discussions: bool
    """
    Whether the repository carries Discussions.
    """

    has_issues: bool
    """
    Whether the repository carries issues.
    """

    has_projects: bool
    """
    Whether the repository carries projects.
    """

    has_wiki: bool
    """
    Whether the repository carries a wiki.
    """

    security_and_analysis: SecurityAndAnalysis
    """
    The secret scanning features the repository runs.
    """

    squash_merge_commit_message: Literal["BLANK", "COMMIT_MESSAGES", "PR_BODY"]
    """
    What a squashed commit's message holds.
    """

    squash_merge_commit_title: Literal["COMMIT_OR_PR_TITLE", "PR_TITLE"]
    """
    What a squashed commit's title holds.
    """


class Task(Record, extra="ignore"):
    """
    One task `mise tasks ls` lists, read for its name, the tasks it depends
    on, the file declaring it, and the scripts a task declared in TOML runs.
    """

    depends: list[str]
    """
    The tasks mise runs before this one.
    """

    name: str
    """
    The task's full name, its group and its verb.
    """

    source: Path
    """
    The absolute path of the file declaring the task.
    """

    run: list[Lines] = []
    """
    The command lines of each script a task declared in TOML runs, keyed
    by the line each opens on, a reference to another task holding none,
    or nothing for a file task, whose own file runs.
    """

    @property
    def file(self) -> Path:
        """
        Names the file declaring the task, relative to the root of the
        checkout, climbing out of it for a task a parent directory declares.
        """
        return self.source.resolve().relative_to(Path.cwd().resolve(), walk_up=True)

    def runs(self, *command: str) -> list[tuple[str, ...]]:
        """
        Lists the words after each place the task's TOML scripts start
        `command`, given as its words (`"uv", "run"`).
        """
        return [
            options
            for lines in self.run
            for words in lines.values()
            for options in following(command, words)
        ]


class SecurityAndAnalysis(Record):
    """
    The `[repository.security_and_analysis]` table, holding the secret
    scanning features the repository runs.
    """

    secret_scanning: Feature
    """
    Whether GitHub scans the repository's history on every branch for a
    secret a known provider issues.
    """

    secret_scanning_push_protection: Feature
    """
    Whether GitHub refuses a push carrying such a secret.
    """


class SiteManifest(JsonFile, extra="ignore"):
    """
    The pins `file` declares for the docs site, each field taken from the
    key its alias names.
    """

    file: ClassVar[Path] = Path("docs/package.json")

    node_types: VersionNumber = Field(
        validation_alias = AliasPath("devDependencies", "@types/node")
    )
    """
    The version of the Node.js types the site's TypeScript is checked
    against.
    """

    pins: dict[str, str] = Field(validation_alias="devDependencies")
    """
    The exact version each package the site depends on is pinned to, under
    the package's name.
    """


class TomlFile(Record):
    """
    The base of a record one TOML file holds whole, which `read` validates
    into the record.
    """

    file: ClassVar[Path]

    @classmethod
    def read(cls) -> Self:
        """
        Reads the record at `file`, raising `Unreadable` where the file
        fails to parse or to validate.
        """
        with Finding.reading(cls.file):
            return cls.model_validate(loads(cls.file.read_text(encoding="utf-8")))


class Tree(Record):
    """
    The files of the checkout git lists, tracked or untracked and not
    ignored, each relative to the root.
    """

    files: list[Path]
    """
    Every file, in sorted order.
    """

    @classmethod
    def read(cls) -> Self:
        """
        Lists the files through `git ls-files`, leaving out one git tracks
        that the working tree no longer holds, and raising `Unreadable` on
        the root where git cannot list them.
        """
        with Finding.reading(Path(".")):
            listing = check_output(
                [
                    "git", "ls-files", "--cached", "--deduplicate",
                    "--exclude-standard", "--others", "-z"
                ],
                encoding = "utf-8"
            )

        return cls(
            files = sorted(filter(Path.is_file, map(Path, listing.split("\0"))))
        )

    def under(self, directory: Path) -> list[Path]:
        """
        Picks each file somewhere under `directory`.
        """
        return [file for file in self.files if file.is_relative_to(directory)]


class Unreadable(Exception):
    """
    Raised where a file a check of `repo:audit` reads fails to parse, its
    arguments the findings reporting each problem the parse met.
    """

    def __str__(self) -> str:
        """
        Joins the message of each finding, one to a line.
        """
        return "\n".join(finding.message for finding in self.args)

    @classmethod
    def gather[T, R](cls, items: Iterable[T], read: Callable[[T], R]) -> list[R]:
        """
        Applies `read` to each of `items`, and once every read has run,
        raises one `Unreadable` holding the findings of each read that
        raised it, chained to the group of those errors.

        Returns:
            What each read returned, in the order of `items`.
        """
        errors  = []
        results = []

        for item in items:
            try:
                results.append(read(item))
            except Unreadable as error:
                errors.append(error)

        if errors:
            raise cls(*chain.from_iterable(error.args for error in errors)) from (
                ExceptionGroup("Each read that failed", errors)
            )

        return results


class ActionsPermissions(Endpoint):
    """
    The `[actions]` table, the body of the request that sets which actions a
    workflow may run.
    """

    path: ClassVar[str] = "actions/permissions"

    allowed_actions: Literal["all", "local_only", "selected"]
    """
    The actions a workflow may run, as GitHub names the choice.
    """

    enabled: bool
    """
    Whether GitHub Actions runs on the repository at all.
    """

    sha_pinning_required: bool
    """
    Whether a workflow may run only an action pinned to a full commit SHA.
    """


class Project(Record, extra="ignore"):
    """
    The `[project]` table of `file`, read for the fields the repository's
    settings take from it and the fields `repo:audit` holds other files to.
    """

    file: ClassVar[Path] = Path("pyproject.toml")

    authors: list[Author]
    """
    The people and the organizations who wrote the package.
    """

    description: str
    """
    The one-sentence summary GitHub shows as the repository's description.
    """

    keywords: list[str]
    """
    The keywords GitHub carries as the repository's topics.
    """

    license: str
    """
    The SPDX expression naming the license the package ships under.
    """

    name: str
    """
    The name the package installs under.
    """

    version: VersionNumber
    """
    The version the package carries.
    """

    license_files: list[Path] = Field(alias="license-files")
    """
    The license files the wheel carries, relative to the root.
    """

    requires_python: Specifiers = Field(alias="requires-python")
    """
    The Python releases the package installs on.
    """

    scripts: dict[str, str] = {}
    """
    Each command the package installs, beside the object it runs, written
    as the module's dotted path, a `:`, and the object's name.
    """

    urls: dict[str, HttpUrl] = {}
    """
    The addresses `[project.urls]` names, the `Homepage` the docs site
    serves at among them.
    """

    @property
    def about(self) -> dict[str, str]:
        """
        Holds the description GitHub shows in the repository's About box,
        beside the homepage where `[project.urls]` names one, as fields of
        the request that updates the repository, so a homepage set by hand
        stays where the project names none.
        """
        return {"description": self.description} | (
            {"homepage": homepage} if (homepage := self.homepage) else {}
        )

    @property
    def credits(self) -> list[str]:
        """
        Names each author `authors` names by name.
        """
        return [author.name for author in self.authors if author.name]

    @property
    def entries(self) -> list[str]:
        """
        Names the module each command `scripts` declares runs an object of,
        as the module's dotted path.
        """
        return [target.partition(":")[0] for target in self.scripts.values()]

    @property
    def homepage(self) -> str | None:
        """
        Writes the `Homepage` address without its scheme or its closing
        slash, the form GitHub shows beside the description.

        Returns:
            The address, or `None` where `[project.urls]` names no
            `Homepage`.
        """
        if url := self.urls.get("Homepage"):
            return f"{url.host}{url.path}".rstrip("/")

        return None

    @property
    def topics(self) -> Command:
        """
        Builds the `PUT` that replaces every topic the repository carries
        with the keywords.
        """
        return Command.api(
            "topics",
            body   = {"names": self.keywords},
            method = HTTPMethod.PUT
        )

    @classmethod
    def read(cls) -> Self:
        """
        Reads the `[project]` table of `file`, raising `Unreadable` where
        the file fails to parse or the table to validate.
        """
        with Finding.reading(cls.file):
            return cls.model_validate(
                loads(cls.file.read_text(encoding="utf-8")).get("project")
            )


class Script(Record):
    """
    One script under `.mise/`, read for the command its shebang starts, the
    command lines a shell script runs, and the inline metadata it declares.
    """

    commands: dict[int, tuple[str, ...]]
    """
    The words of each command line a shell script runs, keyed by the line
    it opens on, or nothing for a Python script, whose body runs no shell.
    """

    metadata: Metadata | None
    """
    The inline metadata the script declares, or `None` where it declares
    none.
    """

    path: Path
    """
    The script, relative to the root of the checkout.
    """

    shebang: tuple[str, ...]
    """
    The words of the command the shebang starts, or nothing where the script
    opens on no shebang.
    """

    @property
    def lines(self) -> dict[int, tuple[str, ...]]:
        """
        Holds the words of every command the script starts, the shebang's on
        line 1, keyed by the line each opens on.
        """
        return ({1: self.shebang} if self.shebang else {}) | self.commands

    @classmethod
    def from_path(cls, path: Path) -> Self:
        """
        Reads the script at `path`, splitting its body into command lines
        unless its `.py` suffix marks it as Python, and raising `Unreadable`
        where a line or the inline metadata fails to parse.
        """
        with Finding.reading(path):
            text  = path.read_text(encoding="utf-8")
            first = text.partition("\n")[0]

            return cls(
                commands = {} if path.suffix == ".py" else command_lines(text),
                metadata = Metadata.from_script(text),
                path     = path,
                shebang  = tuple(split(first[2:])) if first[:2] == "#!" else ()
            )

    def runs(self, *command: str) -> list[tuple[int, tuple[str, ...]]]:
        """
        Pairs each place the script starts `command`, given as its words
        (`"uv", "run"`), with the line it opens on and the words after it.
        """
        return [
            (line, options)
            for line, words in self.lines.items()
            for options in following(command, words)
        ]


class TaskIssue(Record, extra="ignore"):
    """
    One defect `mise tasks validate` reports in a task's definition.
    """

    message: str
    """
    The defect, as mise words it.
    """

    severity: Severity
    """
    Whether mise fails the validation on the defect or only warns.
    """

    task: str
    """
    The task the defect sits in.
    """

    details: str | None = None
    """
    Where the defect sits in the definition, or `None` where mise names
    nothing further.
    """

    @property
    def text(self) -> str:
        """
        Writes the defect as mise words it, followed by where it sits in
        parentheses where mise names that.
        """
        return f"{self.message!r} ({self.details})" if self.details else repr(
            self.message
        )


class YamlFile(Record):
    """
    The base of a YAML file the audit reads, holding the first document
    the file carries, which for a Markdown file is the frontmatter above
    its text.
    """

    directory: ClassVar[Path]

    file: ClassVar[Path]

    path: Path
    """
    The file, relative to the root of the checkout.
    """

    root: Block
    """
    The node the first document opens on.
    """

    text: str
    """
    What the file holds.
    """

    @property
    def anchors(self) -> list[int]:
        """
        Numbers each line of the first document that carries an anchor or
        an alias.
        """
        events = takewhile(
            lambda event: not isinstance(event, DocumentEndEvent),
            parse(self.text, Loader=SafeLoader)
        )

        return [
            event.start_mark.line + 1
            for event in events
            if isinstance(event, NodeEvent) and event.anchor
        ]

    @classmethod
    def from_path(cls, path: Path) -> Self:
        """
        Reads the first document of the YAML file at `path`, building its
        value once so a tag `yaml.safe_load` cannot build fails the read,
        and raising `Unreadable` where the file fails to parse, holds no
        document, or carries such a tag.
        """
        with Finding.reading(path):
            text = path.read_text(encoding="utf-8")
            root = Block(node=next(compose_all(text, Loader=SafeLoader), None))

            root.value

            return cls(path=path, root=root, text=text)

    @classmethod
    def matching(cls, *patterns: str) -> list[Self]:
        """
        Reads every file under `directory` that one of `patterns` matches,
        in the order of its path, raising `Unreadable` once all are read
        where any fails to parse.
        """
        return Unreadable.gather(
            sorted(chain.from_iterable(map(cls.directory.glob, patterns))),
            cls.from_path
        )

    @classmethod
    def read(cls) -> Self:
        """
        Reads the one file `file` names.
        """
        return cls.from_path(cls.file)


class WorkflowStep(Block):
    """
    One step a job of a workflow or a composite action runs.
    """

    @property
    def action(self) -> str | None:
        """
        Names the action the step uses, as `uses` writes it, or `None` for a
        step that runs a script.
        """
        return self.get("uses")

    @cached_property
    def commands(self) -> list[tuple[str, ...]]:
        """
        Splits the step's `run` script into the words of each command line.
        """
        return list(command_lines(str(self.get("run", default=""))).values())

    @property
    def local(self) -> Path | None:
        """
        Names the directory of the action in this repository the step uses,
        written after `./` or after the `$/` that names the repository the
        workflow runs in, or `None` for any other step.
        """
        action = self.action or ""
        return Path(action[2:]) if action[:2] in {"$/", "./"} else None

    @property
    def pinned(self) -> tuple[str, str] | None:
        """
        Splits `uses` into the action and the ref it is pinned to, or `None`
        for an action of this repository, a step naming no ref, or a step
        running a script.
        """
        action, at, ref = (self.action or "").rpartition("@")
        return (action, ref) if at and not self.local else None

    @property
    def tasks(self) -> list[str]:
        """
        Names the task each `mise run` in the step's script starts, every
        task of a chain it joins with `:::` among them, a `$NAME` it starts
        read as the value the step's `env` gives `NAME`.
        """
        env   = {name: str(block.value) for name, block in self.fields("env").items()}
        named = (
            next((word for word in chained if not word.startswith("-")), None)
            for words in self.commands
            for rest in following(("mise", "run"), words)
            for joint, chained in groupby(rest, ":::".__eq__)
            if not joint
        )

        return [
            env.get(task.strip("${}"), task) if task.startswith("$") else task
            for task in named
            if task
        ]

    @property
    def writes_summary(self) -> bool:
        """
        Tells whether a word of the step's script names
        `GITHUB_STEP_SUMMARY`, the file a workflow step appends the workflow
        run's summary to.
        """
        return any(
            "GITHUB_STEP_SUMMARY" in word for words in self.commands for word in words
        )


class Citation(YamlFile):
    """
    The citation `file` declares, read for the fields the manifest also
    declares.
    """

    file: ClassVar[Path] = Path("CITATION.cff")

    @property
    def authors(self) -> dict[str, int]:
        """
        Names each author the citation credits, a person by their given and
        family names and an entity by its name, beside the line the author
        opens on.
        """
        return {
            " ".join(
                filter(None, (author.get("given-names"), author.get("family-names")))
            )
            or str(author.get("name", default="")): author.line
            for author in self.root.entries("authors")
        }


class Finding(Record):
    """
    One divergence a check of `repo:audit` reports, at the file and the line
    it concerns.
    """

    file: Path
    """
    The file the divergence sits in, relative to the root of the checkout.
    """

    message: str
    """
    What diverges, as one sentence.
    """

    line: int | None = None
    """
    The line the divergence sits on, counting from 1, or `None` where it
    concerns the whole file.
    """

    severity: Severity = Severity.ERROR
    """
    Whether the divergence fails the audit or only warns.
    """

    @property
    def annotation(self) -> str:
        """
        Writes the finding as the workflow command GitHub shows as an
        annotation on its file and line, escaping each property and the
        message as the Actions toolkit's `escapeProperty` and `escapeData`
        escape them.
        """
        data       = str.maketrans({"%": "%25", "\n": "%0A", "\r": "%0D"})
        properties = data | str.maketrans({",": "%2C", ":": "%3A"})

        return "::{} {}::{}".format(
            self.severity,
            ",".join(
                f"{key}={str(value).translate(properties)}"
                for key, value in (("file", self.file), ("line", self.line))
                if value is not None
            ),
            self.message.translate(data)
        )

    @classmethod
    def locate(
        cls,
        file     : Path,
        *needles : str,
        message  : str,
        severity : Severity = Severity.ERROR
    ) -> Self:
        """
        Builds the finding on the first line of `file` that holds the last
        of `needles`, searching from the line that holds the one before
        it, so a key and the value it names may share a line, or on no line
        where a needle appears nowhere from there on. A needle counts only
        with no letter, digit, `_`, or `-` against either end, so `bun i`
        never matches a line running `bun install`.
        """
        numbered = list(
            enumerate(file.read_text(encoding="utf-8").splitlines(), start=1)
        )
        line = 1

        for needle in needles:
            whole = rf"(?<![\w-]){escape(needle)}(?![\w-])"
            line  = line and next(
                (number for number, text in numbered[line - 1:] if search(whole, text)),
                None
            )

        return cls(
            file     = file,
            line     = line,
            message  = message,
            severity = severity
        )

    @classmethod
    @contextmanager
    def reading(cls, file: Path) -> Iterator[None]:
        """
        Raises `Unreadable` in place of any error reading or parsing `file`
        inside the block, holding a finding for each field a validation
        refuses and otherwise one finding on the line the parser names.
        """
        try:
            yield
        except ValidationError as error:
            raise Unreadable(
                *(
                    cls(
                        file    = file,
                        message =
                            f"`{file}` fails validation at "
                            + (
                                f"`{'.'.join(map(str, problem['loc']))}`"
                                if problem["loc"]
                                else "its root"
                            )
                            + f" with {problem['msg']!r}"
                    )
                    for problem in error.errors()
                )
            ) from error
        except (OSError, SubprocessError, SyntaxError, ValueError, YAMLError) as error:
            mark = getattr(error, "problem_mark", None)

            raise Unreadable(
                cls(
                    file    = file,
                    line    = mark.line + 1 if mark else getattr(error, "lineno", None),
                    message = (
                        f"Reading `{file}` fails with "
                        f"{' '.join(str(error).split())!r}"
                    )
                )
            ) from error


class Labels(TomlFile):
    """
    The label registry `file` holds, an array of label rows and nothing
    besides.
    """

    file: ClassVar[Path] = Path(".github/labels.toml")

    labels: list[Label]
    """
    Every label the registry declares, in the order of each label's word.
    """

    @property
    def drifted(self) -> list[Label]:
        """
        Picks each label GitHub lacks or carries under another color or
        description.
        """
        return [
            label
            for label in self.labels
            if label.model_dump() != self.live.get(label.name)
        ]

    @cached_property
    def live(self) -> dict[str, dict[str, str]]:
        """
        Reads the name, the color, and the description of each label GitHub
        carries, as `gh label list` returns them, keyed by the label's name.
        """
        # Without `--limit`, `gh label list` returns at most 30 labels.
        rows = Command(
            arguments = (
                "label", "list", "--json",
                ",".join(Label.model_fields),
                "--limit", "1000"
            )
        ).parsed(list[dict[str, str]])

        return {row["name"]: row for row in rows}

    @property
    def names(self) -> frozenset[str]:
        """
        Names every label the registry declares.
        """
        return frozenset(label.name for label in self.labels)

    @property
    def plan(self) -> Plan:
        """
        Writes each label GitHub lacks or carries under another color
        or description, and names each label GitHub carries that no row
        declares.
        """
        return Plan.leaving(
            declared = self.names,
            kind     = "label",
            live     = self.live,
            writes   = (label.command for label in self.drifted)
        )


class Lockfile(TomlFile, extra="ignore"):
    """
    The packages `file` resolves.
    """

    file: ClassVar[Path] = Path("uv.lock")

    packages: list[LockedPackage] = Field(alias="package")
    """
    Every package the lockfile resolves, in its order.
    """

    def resolved(self, name: str) -> list[Version]:
        """
        Lists each version the lockfile resolves for the package `name`
        names, in ascending order, matching names as PEP 503 normalizes
        them, since a package a marker splits resolves to one version per
        platform.
        """
        return sorted(
            package.version
            for package in self.packages
            if package.version and canonicalize_name(package.name) == canonicalize_name(
                name
            )
        )


class Manifest(TomlFile, extra="ignore"):
    """
    The tables of `file` beside `[project]` that `repo:audit` reads, each
    field taken from the key its alias path names.
    """

    file: ClassVar[Path] = Path("pyproject.toml")

    build_constraints: list[Pin] = Field(
        [],
        validation_alias = AliasPath("tool", "uv", "build-constraint-dependencies")
    )
    """
    The pins `[tool.uv]` holds every package a build resolves to.
    """

    build_requirements: list[Pin] = Field(
        validation_alias = AliasPath("build-system", "requires")
    )
    """
    The packages `[build-system]` builds the wheel with.
    """

    packages: list[Path] = Field(
        validation_alias = AliasPath(
            "tool",
            "hatch",
            "build",
            "targets",
            "wheel",
            "packages"
        )
    )
    """
    The directory of each package the wheel carries.
    """

    target_version: str = Field(
        validation_alias = AliasPath("tool", "prose", "target-version")
    )
    """
    The Python release the formatter writes for.
    """

    test_files: list[str] = Field(
        validation_alias = AliasPath("tool", "pytest", "python_files")
    )
    """
    The patterns a file's name matches for pytest to collect it as a test
    module.
    """

    test_paths: list[Path] = Field(
        validation_alias = AliasPath("tool", "pytest", "testpaths")
    )
    """
    The directories pytest collects the suite from.
    """

    test_skips: list[str] = Field(
        validation_alias = AliasPath("tool", "pytest", "norecursedirs")
    )
    """
    The patterns a directory's name matches for pytest to collect nothing
    under it.
    """

    uv_version: Specifiers = Field(
        validation_alias = AliasPath("tool", "uv", "required-version")
    )
    """
    The uv releases `[tool.uv]` lets run against the project.
    """

    def collects(self, path: Path) -> bool:
        """
        Tells whether pytest collects the file at `path` as a test module,
        which holds for a file under a test path whose name matches a
        pattern `test_files` holds, other than a `conftest.py`, and that no
        directory matching a pattern `test_skips` holds.
        """
        return (
            any(path.is_relative_to(root) for root in self.test_paths)
            and path.name != "conftest.py"
            and any(path.match(pattern) for pattern in self.test_files)
            and not any(
                fnmatch(
                    part,
                    skip
                ) for part in path.parent.parts for skip in self.test_skips
            )
        )

    def mirrors(self, test: Path) -> list[Path]:
        """
        Names the module of each package that the test module at `test`
        mirrors, at the path the test module sits at under its test path.
        """
        return [
            package / test.relative_to(root)
            for root in self.test_paths
            if test.is_relative_to(root)
            for package in self.packages
        ]


class MiseConfig(TomlFile, extra="ignore"):
    """
    The tools `file` pins that another file of the checkout repeats.
    """

    file: ClassVar[Path] = Path(".mise/config.toml")

    node: VersionNumber = Field(validation_alias=AliasPath("tools", "node"))
    """
    The Node.js release mise installs, which runs the docs site's tools.
    """

    python: VersionNumber = Field(validation_alias=AliasPath("tools", "python"))
    """
    The Python release mise installs.
    """

    uv: VersionNumber = Field(validation_alias=AliasPath("tools", "uv"))
    """
    The uv release mise installs.
    """


class ReleaseNotes(YamlFile):
    """
    The release-notes categories `file` declares in priority order.
    """

    file: ClassVar[Path] = Path(".github/release.yml")

    @property
    def categories(self) -> list[Block]:
        """
        Reads each category, holding its `title` and the `labels` that file
        a pull request under it.
        """
        return self.root.entries("changelog", "categories")


class Rulesets(Record):
    """
    The rulesets the files under `directory` declare.
    """

    directory: ClassVar[Path] = Path(".github/rulesets")

    rulesets: dict[Path, Ruleset]
    """
    Every ruleset keyed by its file, in the order of the file's name.
    """

    @cached_property
    def live(self) -> dict[str, int]:
        """
        Reads the id of each ruleset the repository carries on every page
        of GitHub's listing, keyed by its name, leaving out a ruleset the
        repository inherits from an organization.
        """
        pages = Command.api(
            "rulesets?includes_parents=false",
            "--paginate",
            "--slurp"
        ).parsed(list[list[GithubRuleset]])

        return {ruleset.name: ruleset.id for ruleset in chain.from_iterable(pages)}

    @property
    def plan(self) -> Plan:
        """
        Updates each ruleset GitHub carries under the name a file declares
        and creates every other one, and names each ruleset GitHub carries
        that no file declares.
        """
        rulesets = self.rulesets.values()

        return Plan.leaving(
            declared = (ruleset.name for ruleset in rulesets),
            kind     = "ruleset",
            live     = self.live,
            writes   = (ruleset.command(self.live) for ruleset in rulesets)
        )

    @classmethod
    def read(cls) -> Self:
        """
        Reads every ruleset a JSON file under `directory` declares, raising
        `Unreadable` once all are read where any fails to parse.
        """
        paths = sorted(cls.directory.glob("*.json"))

        return cls(
            rulesets = dict(zip(paths, Unreadable.gather(paths, Ruleset.from_path)))
        )


class TaskValidation(Record, extra="ignore"):
    """
    What `mise tasks validate --json` prints, read for each defect.
    """

    issues: list[TaskIssue]
    """
    Each defect, in the order mise reports them.
    """


class Scripts(Record):
    """
    The scripts under `directory` that mise runs as a task, a task runs, or
    a task sources.
    """

    directory: ClassVar[Path] = Path(".mise")

    scripts: list[Script]
    """
    Every script, in the order of its path.
    """

    @classmethod
    def read(cls) -> Self:
        """
        Reads each executable file under `tasks/`, which mise runs as
        a task, beside each wrapper under `bin/` and each library under
        `lib/`, raising `Unreadable` once all are read where any fails to
        parse.
        """
        tasks = (
            path
            for path in (cls.directory / "tasks").rglob("*")
            if path.is_file() and path.stat().st_mode & S_IXUSR
        )

        return cls(
            scripts = Unreadable.gather(
                sorted(
                    chain(
                        tasks,
                        (cls.directory / "bin").glob("*"),
                        (cls.directory / "lib").glob("*")
                    )
                ),
                Script.from_path
            )
        )


class Settings(TomlFile):
    """
    The repository settings `file` declares, one table per endpoint keyed by
    the REST field names and a `[dependabot]` table keyed by each endpoint
    it turns on or off, beside the description, the homepage, and the topics
    `project` reads from `pyproject.toml`.
    """

    file: ClassVar[Path] = Path(".github/settings.toml")

    actions: ActionsPermissions
    """
    The Actions permissions.
    """

    dependabot: Dependabot
    """
    The Dependabot endpoints.
    """

    repository: Repository
    """
    The repository's own fields.
    """

    workflow: WorkflowPermissions
    """
    The permissions of the token each workflow run receives.
    """

    @property
    def plan(self) -> Plan:
        """
        Sends every setting, in the order below:

        - The repository's own fields, with the description the project
          declares and its homepage where it declares one
        - The topics, which replace every topic the repository carries
        - Each Dependabot endpoint, turned on through `PUT` or off through
          `DELETE`
        - The Actions permissions, then the workflow token's
        """
        return Plan(
            writes = (
                Command.api(
                    "",
                    body   = self.repository.model_dump() | self.project.about,
                    method = HTTPMethod.PATCH
                ),
                self.project.topics,
                *self.dependabot.commands,
                self.actions.command, self.workflow.command
            )
        )

    @cached_property
    def project(self) -> Project:
        """
        Reads the `[project]` table of `pyproject.toml`, which the
        description, the homepage, and the topics come from.
        """
        return Project.read()


class Tasks(Record):
    """
    The tasks mise lists for the checkout, beside each defect `mise tasks
    validate` reports in their definitions.
    """

    issues: list[TaskIssue]
    """
    Each defect mise reports, in its order.
    """

    tasks: list[Task]
    """
    Every task the checkout declares, leaving out the global ones a
    developer's own configuration adds.
    """

    @property
    def named(self) -> dict[str, Task]:
        """
        Keys each task by its full name.
        """
        return {task.name: task for task in self.tasks}

    def declaring(self, name: str) -> Path:
        """
        Names the file declaring the task `name`, or `.mise/config.toml`
        where mise lists no such task.
        """
        return self.named[name].file if name in self.named else MiseConfig.file

    @classmethod
    def read(cls) -> Self:
        """
        Lists every task the checkout declares through `mise tasks ls` and
        validates each through `mise tasks validate`, which exits 1 where it
        reports an error, raising `Unreadable` on `.mise/config.toml` where
        mise cannot list the tasks or prints a report that fails to parse.
        """
        with Finding.reading(MiseConfig.file):
            tasks = TypeAdapter(list[Task]).validate_json(
                check_output(["mise", "tasks", "ls", "--json", "--local"])
            )
            report = run(
                ["mise", "tasks", "validate", "--json", *(task.name for task in tasks)],
                capture_output = True,
                encoding       = "utf-8"
            )

            return cls(
                issues = TaskValidation.model_validate_json(report.stdout).issues,
                tasks  = tasks
            )


class Template(YamlFile):
    """
    One issue template under `directory`, read for the labels its
    frontmatter sets.
    """

    directory: ClassVar[Path] = Path(".github/ISSUE_TEMPLATE")

    @property
    def labels(self) -> list[str]:
        """
        Names each label the template sets, which its frontmatter writes as
        a list or as one string of names separated by commas.
        """
        labels = self.root.get("labels", default=[])

        if isinstance(labels, str):
            return [label.strip() for label in labels.split(",")]

        return labels


class WorkflowPermissions(Endpoint):
    """
    The `[workflow]` table, the body of the request that sets what the token
    each workflow run receives may do.
    """

    path: ClassVar[str] = "actions/permissions/workflow"

    can_approve_pull_request_reviews: bool
    """
    Whether the token may open or approve a pull request.
    """

    default_workflow_permissions: Literal["read", "write"]
    """
    Whether the token may write to the repository or only read it.
    """


class Templates(Record):
    """
    The issue templates written in Markdown.
    """

    templates: list[Template]
    """
    Every template, in the order of its file's name.
    """

    @classmethod
    def read(cls) -> Self:
        """
        Reads each Markdown file under the directory `Template` names.
        """
        return cls(templates=Template.matching("*.md"))


class StepFile(YamlFile, ABC):
    """
    The base of a YAML file whose steps run shell scripts, which `from_path`
    splits as it reads the file, so a script that fails to split fails the
    read rather than a check.
    """

    @property
    @abstractmethod
    def steps(self) -> list[WorkflowStep]:
        """
        Lists each step the file runs, in order.
        """

    @classmethod
    def from_path(cls, path: Path) -> Self:
        """
        Reads the file at `path` as `YamlFile` reads it, then splits the
        script of each step, raising `Unreadable` where a script fails to
        split.
        """
        record = super().from_path(path)

        with Finding.reading(path):
            for step in record.steps:
                step.commands

        return record


class Action(StepFile):
    """
    One action manifest under `directory`, read for the inputs it declares
    and the steps a composite action runs.
    """

    directory: ClassVar[Path] = Path(".github/actions")

    @property
    def inputs(self) -> list[str]:
        """
        Names each input the manifest declares.
        """
        return list(self.root.fields("inputs"))

    @cached_property
    def steps(self) -> list[WorkflowStep]:
        """
        Reads each step a composite action runs, in order.
        """
        return [WorkflowStep(node=step.node) for step in self.root.entries(
            "runs",
            "steps"
        )]


class WorkflowJob(Block):
    """
    One job a workflow declares, under the id the workflow keys it by.
    """

    key: str
    """
    The id the workflow keys the job by, which another job's `needs` names.
    """

    inherited: str | None = None
    """
    The `cache-mode` the workflow sets for every job that sets none of its
    own, or `None` where the workflow sets none.
    """

    @property
    def always(self) -> bool:
        """
        Tells whether the job runs under `if: always()`, written bare or
        inside `${{ }}`, so it runs whatever the jobs it waits on end in.
        """
        return (
            str(self.get("if", default=""))
            .removeprefix("${{")
            .removesuffix("}}")
            .strip()
        ) == "always()"

    @property
    def cache_mode(self) -> str | None:
        """
        Names the `cache-mode` the job runs under, its own or else its
        workflow's.
        """
        return self.get("cache-mode", default=self.inherited)

    @property
    def needs(self) -> list[str]:
        """
        Names each job the job waits on, which `needs` writes as one id or a
        list of them.
        """
        needs = self.get("needs", default=[])
        return [needs] if isinstance(needs, str) else needs

    @cached_property
    def steps(self) -> list[WorkflowStep]:
        """
        Reads each step the job runs, in order.
        """
        return [WorkflowStep(node=step.node) for step in self.entries("steps")]

    @property
    def tasks(self) -> list[str]:
        """
        Names each task the job's steps start through `mise run`, a matrix
        expression expanded into every value it takes.
        """
        return [
            task
            for step in self.steps
            for named in step.tasks
            for task in self.expand(named)
        ]

    def expand(self, text: str) -> list[str]:
        """
        Lists each value `text` takes across the job's matrix, from the
        matrix's own axis and from each `include` row setting the key, where
        `text` is one `${{ matrix.<key> }}` expression, reading an axis or
        an `include` written as one expression as no value.

        Returns:
            The values in the order the matrix gives them, or `text` alone
            where it is no such expression.
        """
        if not (expression := fullmatch(r"\$\{\{\s*matrix\.([\w-]+)\s*\}\}", text)):
            return [text]

        key    = expression[1]
        values = chain(
            self.entries("strategy", "matrix", key),
            (row.at(key) for row in self.entries("strategy", "matrix", "include"))
        )

        return list(dict.fromkeys(str(block.value) for block in values if block))

    def inputs(self, name: str) -> list[tuple[WorkflowStep, str]]:
        """
        Pairs each step passing an action of this repository the input
        `name` with each value the input takes across the job's matrix.
        """
        return [
            (step, value)
            for step in self.steps
            if step.local and (given := step.get("with", name)) is not None
            for value in self.expand(str(given))
        ]


class Actions(Record):
    """
    The action manifests under the directory `Action` names, one per action
    the repository declares.
    """

    actions: list[Action]
    """
    Every manifest, in the order of its path.
    """

    @property
    def manifests(self) -> dict[Path, Action]:
        """
        Keys each manifest by the directory a step's `uses` names it by.
        """
        return {action.path.parent: action for action in self.actions}

    @property
    def steps(self) -> list[tuple[Path, WorkflowStep]]:
        """
        Pairs each step a composite action runs with the manifest declaring
        it.
        """
        return [(action.path, step) for action in self.actions for step in action.steps]

    @classmethod
    def read(cls) -> Self:
        """
        Reads the `action.yml` or `action.yaml` in each directory under the
        directory `Action` names.
        """
        return cls(actions=Action.matching("*/action.yml", "*/action.yaml"))


class Workflow(StepFile):
    """
    One workflow under `directory`, read for its triggers and its jobs.
    """

    directory: ClassVar[Path] = Path(".github/workflows")

    @cached_property
    def jobs(self) -> list[WorkflowJob]:
        """
        Reads each job the workflow declares, in the order it declares them,
        each taking the workflow's `cache-mode` where it sets none of its
        own.
        """
        return [
            WorkflowJob(inherited=self.root.get("cache-mode"), key=key, node=job.node)
            for key, job in self.root.fields("jobs").items()
        ]

    @property
    def pulls(self) -> bool:
        """
        Tells whether a pull request runs the workflow.
        """
        return "pull_request" in self.triggers

    @property
    def steps(self) -> list[WorkflowStep]:
        """
        Lists each step a job of the workflow runs, job by job.
        """
        return [step for job in self.jobs for step in job.steps]

    @property
    def triggers(self) -> dict[str, Block | None]:
        """
        Keys the configuration of each event the workflow runs on by the
        event's name, which `on` writes as one name, a list of names, or a
        mapping of each name to its configuration.

        Returns:
            Each event's configuration, or `None` for an event written with
            none.
        """
        if (on := self.root.at("on")) is None:
            return {}

        if fields := on.fields():
            return fields

        return dict.fromkeys(
            map(str, on.value if isinstance(on.value, list) else [on.value])
        )

    def pushes(self, file: Path) -> bool:
        """
        Tells whether a push touching `file` alone runs the workflow, which
        holds for no file where the workflow runs on no push and for every
        file where `on.push` filters no paths. Under `paths`, the last
        pattern `admits` matches decides, one opening on `!` leaving the
        file out, and under `paths-ignore`, any pattern matching it leaves
        it out.
        """
        if "push" not in self.triggers:
            return False

        if ignored := self.root.entries("on", "push", "paths-ignore"):
            return not any(admits(file, str(pattern.value)) for pattern in ignored)

        if (paths := self.root.at("on", "push", "paths")) is None:
            return True

        return next(
            (
                not pattern.startswith("!")
                for pattern in (str(entry.value) for entry in reversed(paths.entries()))
                if admits(file, pattern.removeprefix("!"))
            ),
            False
        )


class Workflows(Record):
    """
    The workflows under the directory `Workflow` names.
    """

    workflows: list[Workflow]
    """
    Every workflow, in the order of its file's name.
    """

    @property
    def jobs(self) -> list[tuple[Path, WorkflowJob]]:
        """
        Pairs each job a workflow declares with the workflow declaring it.
        """
        return [(
            workflow.path, job
        ) for workflow in self.workflows for job in workflow.jobs]

    @property
    def steps(self) -> list[tuple[Path, WorkflowStep]]:
        """
        Pairs each step a job of a workflow runs with the workflow declaring
        it.
        """
        return [
            (workflow.path, step)
            for workflow in self.workflows
            for step in workflow.steps
        ]

    @classmethod
    def read(cls) -> Self:
        """
        Reads each `.yml` or `.yaml` file under the directory `Workflow`
        names.
        """
        return cls(workflows=Workflow.matching("*.yml", "*.yaml"))