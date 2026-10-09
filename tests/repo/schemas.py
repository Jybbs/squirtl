"""
Pins what each registry record reads and the plan it derives, covering:

- The rows a label refuses, and the longest description it takes
- The labels a plan writes and the live labels it lists as strays
- The rulesets a plan updates in place, creates, and lists as strays
- The tables and the fields the settings refuse, and the order the settings
  send in
- The homepage the project writes without its scheme

Each case writes the files it reads into a checkout under `tmp_path`, and
the `fp` fixture pytest-subprocess provides answers every `gh` read, so no
case reaches GitHub.
"""

from collections.abc   import Callable, Mapping
from http              import HTTPMethod
from json              import dumps, loads
from pathlib           import Path
from pydantic          import ValidationError
from pytest            import MonkeyPatch, fixture, mark, param, raises
from pytest_subprocess import FakeProcess

from squirtl.repo.github  import Command
from squirtl.repo.schemas import Label, Labels, Project, Rulesets, Settings


@fixture
def checkout(
    monkeypatch : MonkeyPatch,
    tmp_path    : Path
) -> Callable[[Mapping[str, str]], None]:
    """
    Builds a writer that makes `tmp_path` the working directory and writes
    each file a case names there, under its path relative to that directory.
    """
    monkeypatch.chdir(tmp_path)

    def write(files: Mapping[str, str]):
        """
        Writes each of `files`, a path beside the text it holds.
        """
        for path, text in files.items():
            (file := tmp_path / path).parent.mkdir(exist_ok=True, parents=True)
            file.write_text(text, encoding="utf-8")

    return write


@fixture
def ruleset() -> Callable[..., str]:
    """
    Builds a writer of one ruleset file's JSON, an active ruleset on a
    branch with no conditions and no rules unless a case sets other fields.
    """
    return lambda **fields: dumps(
        {
            "enforcement"   : "active",
            "name"          : "main",
            "target"        : "branch",
            "bypass_actors" : [],
            "conditions"    : {},
            "rules"         : []
        }
        | fields
    )


@fixture
def settings(checkout: Callable[[Mapping[str, str]], None]) -> Callable[..., Settings]:
    """
    Builds a reader of the settings a case poses, which
    copies `fixtures/settings.toml`, declaring every field, to
    `.github/settings.toml` once each rewrite the case passes is applied,
    beside a `pyproject.toml` declaring a description, two keywords, and the
    homepage the case names.

    Returns:
        A function taking pairs of text to replace and text to replace it
        with, and a `homepage` line for `[project.urls]`, which returns the
        settings those files declare.
    """
    def read(*rewrites: tuple[str, str], homepage: str = "") -> Settings:
        """
        Writes both files and reads them as `Settings`.
        """
        declared = (Path(__file__).parent / "fixtures/settings.toml").read_text(
            encoding = "utf-8"
        )

        for old, new in rewrites:
            declared = declared.replace(old, new)

        checkout(
            {
                ".github/settings.toml" : declared,
                "pyproject.toml"        : (
                    '[project]\ndescription = "Plays."\nkeywords = ["dqn", "pyboy"]\n'
                    f"name = 'squirtl'\n\n[project.urls]\n{homepage}\n"
                )
            }
        )

        return Settings.read()

    return read


def test_a_description_takes_the_100_characters_github_accepts():
    """
    Pins that a description at the 100 characters GitHub accepts reads, the
    longest the registry takes.
    """
    assert Label(color="3aa6f0", description="x" * 100, name="🧢 agent")


@mark.parametrize(
    "row",
    [
        param({"color": "3AA6F0"}, id="uppercase-color"),
        param({"color": "#3aa6f0"}, id="hashed-color"),
        param({"color": "3aa6f"}, id="five-digits"),
        param({"description": "x" * 101}, id="101-characters"),
        param({"emoji": "🧢"}, id="unknown-key")
    ]
)
def test_a_label_refuses_a_malformed_row(row: dict[str, str]):
    """
    Pins that a label refuses a color other than six lowercase hexadecimal
    digits, a description past the 100 characters GitHub accepts, and a key
    no field declares, so a misshapen row fails before anything is sent.
    """
    with raises(ValidationError):
        Label.model_validate(
            {"color": "3aa6f0", "description": "The agent", "name": "🧢 agent"} | row
        )


def test_the_label_plan_writes_each_label_github_lacks_or_carries_differently(
    checkout : Callable[[Mapping[str, str]], None],
    fp       : FakeProcess
):
    """
    Pins that the label plan leaves alone a label GitHub carries as the
    registry declares it, writes one GitHub lacks and one it carries under
    another color or another description, in the registry's order, and lists
    each live label no row declares in sorted order, reading every field
    `Label` declares from `gh label list` past its default 30.
    """
    rows = [
        {"color": "3aa6f0", "description": "The agent", "name": "🧢 agent"},
        {"color": "b8d93a", "description": "A defect", "name": "🐛 bug"},
        {"color": "5f6672", "description": "The build", "name": "🔧 build"},
        {"color": "e6e6ff", "description": "The command", "name": "⌨️ cli"}
    ]

    checkout(
        {
            ".github/labels.toml": "".join(
                f'[[labels]]\ncolor = "{row["color"]}"\n'
                f'description = "{row["description"]}"\nname = "{row["name"]}"\n\n'
                for row in rows
            )
        }
    )
    fp.register(
        ["gh", "label", "list", "--json", "color,description,name", "--limit", "1000"],
        stdout = dumps(
            [
                rows[0],
                rows[1] | {"color": "ffffff"},
                rows[3] | {"description": "The old command"},
                {"color": "ffffff", "description": "", "name": "wontfix"},
                {"color": "cfd3d7", "description": "", "name": "duplicate"}
            ]
        )
    )
    plan = Labels.read().plan

    assert plan.strays == ("the label duplicate", "the label wontfix")
    assert plan.writes == tuple(Label.model_validate(row).command for row in rows[1:])


def test_the_label_registry_refuses_a_key_beside_its_rows(
    checkout: Callable[[Mapping[str, str]], None]
):
    """
    Pins that a key at the registry's top level fails the read, since the
    registry holds its rows and nothing besides.
    """
    checkout(
        {
            ".github/labels.toml": (
                'version = 1\n\n[[labels]]\ncolor = "3aa6f0"\n'
                'description = "The agent"\nname = "🧢 agent"\n'
            )
        }
    )

    with raises(ValidationError):
        Labels.read()


@mark.parametrize(
    ("urls", "homepage"),
    [
        param({}, "", id="none"),
        param(
            {"Homepage": "https://jybbs.github.io/squirtl/"},
            "jybbs.github.io/squirtl",
            id = "a-path"
        ),
        param({"Homepage": "https://example.org"}, "example.org", id="a-host"),
        param(
            {"Repository": "https://github.com/Jybbs/squirtl"},
            "",
            id = "another-address"
        )
    ]
)
def test_the_homepage_drops_its_scheme_and_closing_slash(
    homepage : str,
    urls     : dict[str, str]
):
    """
    Pins that the homepage the settings send is the `Homepage` address
    without its scheme or its closing slash, keeping its path, and an empty
    string where `[project.urls]` names no `Homepage`.
    """
    assert Project(description="Plays.", keywords=[], urls=urls).homepage == homepage


def test_the_ruleset_plan_updates_a_live_ruleset_and_creates_any_other(
    checkout : Callable[[Mapping[str, str]], None],
    fp       : FakeProcess,
    ruleset  : Callable[..., str]
):
    """
    Pins that the ruleset plan sends a ruleset GitHub carries under the
    same name as a `PUT` to its id and any other as a `POST`, each with the
    body its file declares, in the order of the files' names, and lists the
    live ruleset no file declares, reading every page of the repository's
    own rulesets.
    """
    checkout(
        {
            ".github/rulesets/main.json" : ruleset(name="main"),
            ".github/rulesets/tags.json" : ruleset(name="tags", target="tag")
        }
    )
    fp.register(
        [
            "gh", "api", "repos/{owner}/{repo}/rulesets?includes_parents=false",
            "--method", "GET",
            "--paginate", "--slurp"
        ],
        stdout = dumps(
            [
                [{"id": 7, "name": "main", "target": "branch"}],
                [{"id": 9, "name": "legacy"}]
            ]
        )
    )
    plan = Rulesets.read().plan

    assert plan.strays == ("the ruleset legacy",)
    assert plan.writes == (
        Command.api(
            "rulesets/7",
            body   = loads(ruleset(name="main")),
            method = HTTPMethod.PUT
        ),
        Command.api(
            "rulesets",
            body   = loads(ruleset(name="tags", target="tag")),
            method = HTTPMethod.POST
        )
    )


@mark.parametrize(
    "fields",
    [
        param({"targets": "tag"}, id="misspelled-key"),
        param({"target": "tags"}, id="unknown-target")
    ]
)
def test_a_ruleset_refuses_a_key_or_a_target_github_does_not_take(
    checkout : Callable[[Mapping[str, str]], None],
    fields   : dict[str, str],
    ruleset  : Callable[..., str]
):
    """
    Pins that a ruleset file holding a key no field declares or a target
    GitHub does not take fails the read before anything is sent.
    """
    checkout({".github/rulesets/main.json": ruleset(**fields)})

    with raises(ValidationError):
        Rulesets.read()


@mark.parametrize(
    "rewrite",
    [
        param(("has_wiki ", "has_wikis = false\nhas_wiki "), id="unknown-field"),
        param(("has_issues", "#has_issues"), id="missing-field"),
        param(('"read"', '"none"'), id="unknown-value"),
        param(
            ("[workflow]", '[project]\ndescription = "x"\n\n[workflow]'),
            id = "project-table"
        )
    ]
)
def test_the_settings_refuse_a_table_or_a_field_no_record_declares(
    rewrite  : tuple[str, str],
    settings : Callable[..., Settings]
):
    """
    Pins that the settings fail the read on a table or a field no record
    declares, a field left out, a value GitHub does not take, and a
    `[project]` table of their own, so nothing is sent before a mistake in
    the file surfaces.
    """
    with raises(ValidationError):
        settings(rewrite)


def test_the_settings_send_every_setting_in_the_order_the_endpoints_take(
    settings: Callable[..., Settings]
):
    """
    Pins that the settings send the repository's own fields with the
    project's description and homepage, then the project's keywords as the
    topics, then each Dependabot endpoint turned off or on, then the Actions
    permissions and the workflow token's, each through the method its
    endpoint takes.
    """
    writes = settings(
        homepage = 'Homepage = "https://jybbs.github.io/squirtl/"'
    ).plan.writes

    assert [(write.arguments[1], write.arguments[3]) for write in writes] == [
        ("repos/{owner}/{repo}", "PATCH"),
        ("repos/{owner}/{repo}/topics", "PUT"),
        ("repos/{owner}/{repo}/automated-security-fixes", "DELETE"),
        ("repos/{owner}/{repo}/vulnerability-alerts", "PUT"),
        ("repos/{owner}/{repo}/actions/permissions", "PUT"),
        ("repos/{owner}/{repo}/actions/permissions/workflow", "PUT")
    ]
    assert {key: writes[0].body[key] for key in ("description", "homepage")} == {
        "description" : "Plays.",
        "homepage"    : "jybbs.github.io/squirtl"
    }
    assert writes[1].body == {"names": ["dqn", "pyboy"]}
