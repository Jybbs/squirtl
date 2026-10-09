"""
Defines the records the `repo:labels` and `repo:rulesets` tasks read from
the registries under `.github/` and from `pyproject.toml`, each registry
deriving the `Plan` that brings GitHub in line with it:

- `Schema`, the base each record builds on, and `Registry`, the base of a
  registry one TOML file holds
- `Label` and `Labels`, the label registry
- `Ruleset` and `Rulesets`, the rulesets, beside `GithubRuleset`
- `Settings` and a record for each of its tables, beside `Project`
"""

from collections.abc import Mapping
from functools       import cached_property
from http            import HTTPMethod
from itertools       import chain
from pathlib         import Path
from pydantic        import BaseModel, Field, HttpUrl, JsonValue, StringConstraints, TypeAdapter
from tomllib         import loads
from typing          import Annotated, ClassVar, Literal, Self

from squirtl.repo.github import Command, Plan


class Schema(BaseModel, extra="forbid", frozen=True, use_attribute_docstrings=True):
    """
    The base each record this module reads builds on, which refuses an
    assignment once built and takes the docstring beneath each field as
    its description. A registry's record refuses a key no field declares,
    so a misspelled key fails the read before anything is sent, whereas a
    record of what GitHub or the manifest returns ignores the keys it does
    not read.
    """


class ActionsPermissions(Schema):
    """
    The `[actions]` table, the body of the request that sets which actions a
    workflow may run.
    """

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

    @property
    def command(self) -> Command:
        """
        Builds the `PUT` that sets which actions a workflow may run.
        """
        return Command.api(
            "actions/permissions",
            body   = self.model_dump(),
            method = HTTPMethod.PUT
        )


class Dependabot(Schema):
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


class Feature(Schema):
    """
    One feature `security_and_analysis` turns on or off.
    """

    status: Literal["disabled", "enabled"]
    """
    Whether the feature is on.
    """


class GithubRuleset(Schema, extra="ignore"):
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


class Label(Schema):
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


class Project(Schema, extra="ignore"):
    """
    The `[project]` table of `file`, read for the fields the repository's
    settings take from it.
    """

    file: ClassVar[Path] = Path("pyproject.toml")

    description: str
    """
    The one-sentence summary GitHub shows as the repository's description.
    """

    keywords: list[str]
    """
    The keywords GitHub carries as the repository's topics.
    """

    urls: dict[str, HttpUrl] = {}
    """
    The addresses `[project.urls]` names, the `Homepage` among them once the
    docs site serves.
    """

    @property
    def about(self) -> dict[str, str]:
        """
        Holds the description and the homepage GitHub shows in the
        repository's About box, as fields of the request that updates the
        repository.
        """
        return {"description": self.description, "homepage": self.homepage}

    @property
    def homepage(self) -> str:
        """
        Writes the `Homepage` address without its scheme or its closing
        slash, the form GitHub shows beside the description, or an empty
        string where `[project.urls]` names no `Homepage`.
        """
        if url := self.urls.get("Homepage"):
            return f"{url.host}{url.path}".rstrip("/")

        return ""

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
        Reads the `[project]` table of `file`.
        """
        return cls.model_validate(
            loads(cls.file.read_text(encoding="utf-8"))["project"]
        )


class Registry(Schema):
    """
    The base of a registry one TOML file under `.github/` holds whole, which
    `read` validates into the record.
    """

    file: ClassVar[Path]

    @classmethod
    def read(cls) -> Self:
        """
        Reads the registry at `file`.
        """
        return cls.model_validate(loads(cls.file.read_text(encoding="utf-8")))


class Repository(Schema):
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


class Ruleset(Schema):
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


class Labels(Registry):
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
        rows = TypeAdapter(list[dict[str, str]]).validate_json(
            Command(
                arguments = (
                    "label", "list", "--json",
                    ",".join(Label.model_fields),
                    "--limit", "1000"
                )
            ).output()
        )

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


class Rulesets(Schema):
    """
    The rulesets the files under `directory` declare.
    """

    directory: ClassVar[Path] = Path(".github/rulesets")

    rulesets: list[Ruleset]
    """
    Every ruleset, in the order of its file's name.
    """

    @cached_property
    def live(self) -> dict[str, int]:
        """
        Reads the id of each ruleset the repository carries on every page
        of GitHub's listing, keyed by its name, leaving out a ruleset the
        repository inherits from an organization.
        """
        pages = TypeAdapter(list[list[GithubRuleset]]).validate_json(
            Command.api(
                "rulesets?includes_parents=false",
                "--paginate",
                "--slurp"
            ).output()
        )

        return {ruleset.name: ruleset.id for ruleset in chain.from_iterable(pages)}

    @property
    def plan(self) -> Plan:
        """
        Updates each ruleset GitHub carries under the name a file declares
        and creates every other one, and names each ruleset GitHub carries
        that no file declares.
        """
        return Plan.leaving(
            declared = (ruleset.name for ruleset in self.rulesets),
            kind     = "ruleset",
            live     = self.live,
            writes   = (ruleset.command(self.live) for ruleset in self.rulesets)
        )

    @classmethod
    def read(cls) -> Self:
        """
        Reads every ruleset a JSON file under `directory` declares.
        """
        return cls(
            rulesets = [
                Ruleset.model_validate_json(path.read_text(encoding="utf-8"))
                for path in sorted(cls.directory.glob("*.json"))
            ]
        )


class SecurityAndAnalysis(Schema):
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


class Settings(Registry):
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

        - The repository's own fields, with the description and the homepage
          the project declares
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


class WorkflowPermissions(Schema):
    """
    The `[workflow]` table, the body of the request that sets what the token
    each workflow run receives may do.
    """

    can_approve_pull_request_reviews: bool
    """
    Whether the token may open or approve a pull request.
    """

    default_workflow_permissions: Literal["read", "write"]
    """
    Whether the token may write to the repository or only read it.
    """

    @property
    def command(self) -> Command:
        """
        Builds the `PUT` that sets what the token each workflow run receives
        may do.
        """
        return Command.api(
            "actions/permissions/workflow",
            body   = self.model_dump(),
            method = HTTPMethod.PUT
        )
