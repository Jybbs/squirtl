"""
Pins what each registry record reads and the plan it derives, covering:

- The rows a label refuses, and the longest description it takes
- The labels a plan writes and the live labels it lists as strays
- The rulesets a plan updates in place, creates, and lists as strays
- The tables, the fields, and the values the settings refuse, the assignment
  they refuse once read, and the order the settings send in
- The homepage the project writes without its scheme, and the settings
  leaving it out where the project names none
- The findings a file failing to parse becomes, and the line a finding
  locates
- How a shell script splits into command lines, how a script's inline
  metadata reads, and how a YAML node reads its keys, its triggers, and
  its matrix
- The files git lists and the tasks mise lists and validates

Each case writes the files it reads under `tmp_path` through the `checkout`
fixture, and the `fp` fixture pytest-subprocess provides answers every `gh`,
`git`, and `mise` command, so no case starts any of them.
"""

from collections.abc   import Callable, Mapping
from http              import HTTPMethod
from json              import dumps, loads
from pathlib           import Path
from pydantic          import ValidationError
from pytest            import fixture, mark, param, raises
from pytest_subprocess import FakeProcess
from textwrap          import dedent
from yaml              import compose

from squirtl.repo.github  import Command
from squirtl.repo.schemas import (
    Block, Finding, Label, Labels, Manifest, Metadata, Project, Rulesets, Script,
    Settings, Task, Tasks, Template, Tree, Unreadable, Workflow, YamlFile, command_lines
)


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
def settings(
    checkout : Callable[[Mapping[str, str]], None],
    manifest : str
) -> Callable[..., Settings]:
    """
    Builds a reader of the settings a case poses, which
    copies `fixtures/settings.toml`, declaring every field, to
    `.github/settings.toml` once each rewrite the case passes is applied,
    beside the `manifest` fixture's `pyproject.toml` with the homepage the
    case names.

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
                "pyproject.toml"        : f"{manifest}\n[project.urls]\n{homepage}\n"
            }
        )

        return Settings.read()

    return read


def test_a_block_reads_only_the_shape_its_node_holds():
    """
    Pins that a block holding a scalar reads no fields and no entries, one
    holding a mapping no entries, and one holding a sequence no fields, and
    that `get` falls back to its default for a missing key and for a key
    holding null.
    """
    block = Block(node=compose("a: [1]\nb: c\nn:\n"))

    assert (block.entries(), block.fields("b"), block.fields("a")) == ([], {}, {})
    assert block.get("a") == [1]
    assert block.get("z", default=0) == 0
    assert block.get("n", default=[]) == []
    assert block.at("b", "c") is None


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


def test_a_description_takes_the_100_characters_github_accepts():
    """
    Pins that a description at the 100 characters GitHub accepts reads, the
    longest the registry takes.
    """
    assert Label(color="3aa6f0", description="x" * 100, name="🧢 agent")


def test_a_matrix_expression_expands_into_the_values_its_axis_and_rows_give(
    checkout: Callable[[Mapping[str, str]], None]
):
    """
    Pins that a `${{ matrix.<key> }}` expression expands into each value
    the matrix's own axis gives and each `include` row setting the key, once
    each and in that order, into nothing where the axis and `include` are
    each one expression, and that any other text stays as it is.
    """
    checkout(
        {
            "ci.yml": dedent(
                """
                jobs:
                  check:
                    strategy:
                      matrix:
                        tools: [python uv, zizmor]
                        include:
                          - tools: bun
                          - tools: zizmor
                          - name: x
                  dynamic:
                    strategy:
                      matrix:
                        tools   : ${{ fromJSON(needs.plan.outputs.tools) }}
                        include : ${{ fromJSON(needs.plan.outputs.rows) }}
                """
            )
        }
    )
    [job, dynamic] = Workflow.from_path(Path("ci.yml")).jobs

    assert job.expand("${{ matrix.tools }}") == ["python uv", "zizmor", "bun"]
    assert job.expand("python uv") == ["python uv"]
    assert dynamic.expand("${{ matrix.tools }}") == []


@mark.parametrize(
    ("urls", "homepage"),
    [
        param({}, None, id="none"),
        param(
            {"Homepage": "https://jybbs.github.io/squirtl/"},
            "jybbs.github.io/squirtl",
            id = "a-path"
        ),
        param({"Homepage": "https://example.org"}, "example.org", id="a-host"),
        param(
            {"Repository": "https://github.com/Jybbs/squirtl"},
            None,
            id = "another-address"
        )
    ]
)
def test_the_homepage_drops_its_scheme_and_closing_slash(
    homepage : str | None,
    urls     : dict[str, str]
):
    """
    Pins that the homepage the settings send is the `Homepage` address
    without its scheme or its closing slash, keeping its path, and `None`
    where `[project.urls]` names no `Homepage`.
    """
    project = Project.model_validate(
        {
            "description"     : "Plays.",
            "license"         : "MIT",
            "name"            : "squirtl",
            "requires-python" : ">=3.14",
            "urls"            : urls,
            "version"         : "0.1.0",
            "authors"         : [],
            "keywords"        : [],
            "license-files"   : []
        }
    )

    assert project.homepage == homepage


def test_a_script_with_an_unclosed_quote_is_unreadable(
    checkout: Callable[[Mapping[str, str]], None]
):
    """
    Pins that a shell script whose quote never closes raises `Unreadable`
    naming the script rather than ending the audit.
    """
    checkout({".mise/tasks/py/test": "#!/bin/sh\necho 'open\n"})

    with raises(Unreadable, match="Reading `.mise/tasks/py/test` fails"):
        Script.from_path(Path(".mise/tasks/py/test"))


@mark.parametrize(
    "fields",
    [
        param({"targets": "tag"}, id="misspelled-key"),
        param({"target": "tags"}, id="unknown-target"),
        param({"enforcement": "on"}, id="unknown-enforcement")
    ]
)
def test_a_ruleset_refuses_a_key_or_a_value_github_does_not_take(
    checkout : Callable[[Mapping[str, str]], None],
    fields   : dict[str, str],
    ruleset  : Callable[..., str]
):
    """
    Pins that a ruleset file holding a key no field declares or a value
    GitHub does not take fails the read before anything is sent.
    """
    checkout({".github/rulesets/main.json": ruleset(**fields)})

    with raises(Unreadable):
        Rulesets.read()


@mark.parametrize(
    "rewrite",
    [
        param(("has_wiki ", "has_wikis = false\nhas_wiki "), id="unknown-field"),
        param(("has_issues", "#has_issues"), id="missing-field"),
        param(('"all"', '"every"'), id="unknown-allowed-actions"),
        param(('"enabled" }', '"on" }'), id="unknown-feature-status"),
        param(('"PR_TITLE"', '"TITLE"'), id="unknown-squash-title"),
        param(('"read"', '"none"'), id="unknown-token-permission"),
        param(
            ("[workflow]", '[project]\ndescription = "x"\n\n[workflow]'),
            id = "project-table"
        )
    ]
)
def test_the_settings_refuse_a_table_a_field_or_a_value_github_does_not_take(
    rewrite  : tuple[str, str],
    settings : Callable[..., Settings]
):
    """
    Pins that the settings fail the read on a table or a field no record
    declares, a field left out, a value GitHub does not take, and a
    `[project]` table of their own, so nothing is sent before a mistake in
    the file surfaces.
    """
    with raises(Unreadable):
        settings(rewrite)


@mark.parametrize(
    "assign",
    [
        param(lambda read: setattr(read, "workflow", read.workflow), id="a-table"),
        param(lambda read: setattr(read.repository, "has_wiki", True), id="a-field")
    ]
)
def test_the_settings_refuse_an_assignment_once_read(
    assign   : Callable[[Settings], None],
    settings : Callable[..., Settings]
):
    """
    Pins that the settings record refuses an assignment once read, to one of
    its tables and to a field of one table alike.
    """
    with raises(ValidationError):
        assign(settings())


def test_a_test_module_is_collected_as_pytest_collects_it(
    checkout : Callable[[Mapping[str, str]], None],
    manifest : str
):
    """
    Pins that the manifest collects a file under a test path matching a
    pattern `python_files` holds, other than a `conftest.py` or a file under
    a directory `norecursedirs` names, and mirrors it under each package.
    """
    checkout({"pyproject.toml": manifest})
    read = Manifest.read()

    assert [
        read.collects(Path(path))
        for path in (
            "tests/repo/checks.py", "tests/conftest.py", "tests/common/x.py",
            "tests/a.txt", "src/x.py"
        )
    ] == [True, False, False, False, False]
    assert read.mirrors(Path("tests/repo/checks.py")) == [Path(
        "src/squirtl/repo/checks.py"
    )]


def test_command_lines_join_continued_lines_and_drop_comments():
    """
    Pins that a shell script splits into the words of each command line,
    keyed by the line it opens on, a line ending in a backslash joined to
    the next, a comment and a blank line left out, each of `(`, `)`, and
    `&&` standing as a word of its own, and a quoted substitution followed
    by the words of the command inside it up to the `)` closing it, so a
    quote after that `)` is never read as the command's, or to the end of
    the word where no `)` closes it, as in a single-quoted literal.
    """
    assert command_lines(
        'set -e  # strict\n\nx=$(uv run a) && \\\n  b "c d"\nv="$(uv run b)"\n'
        'echo "$(git rev-parse HEAD) is the head\'s commit"\n'
        "echo '$(uv run c'\n"
    ) == {
        1 : ("set", "-e"),
        3 : ("x=$", "(", "uv", "run", "a", ")", "&&", "b", "c d"),
        5 : ("v=$(uv run b)", "uv", "run", "b"),
        6 : (
            "echo", "$(git rev-parse HEAD) is the head's commit", "git",
            "rev-parse", "HEAD"
        ),
        7 : ("echo", "$(uv run c", "uv", "run", "c")
    }


@mark.parametrize(
    ("path", "text", "read", "line", "message"),
    [
        param(
            ".github/labels.toml",
            "a = 1\nb = \n",
            Labels.read,
            2,
            "Reading `.github/labels.toml` fails with 'Invalid value",
            id = "toml"
        ),
        param(
            "a.yml",
            "a: [1, 2\nb: 3\n",
            lambda: YamlFile.from_path(Path("a.yml")),
            2,
            "Reading `a.yml` fails with 'while parsing a flow sequence",
            id = "yaml"
        ),
        param(
            "a.yml",
            "",
            lambda: YamlFile.from_path(Path("a.yml")),
            None,
            "`a.yml` fails validation at `node`",
            id = "no-document"
        ),
        param(
            "b.yml",
            None,
            lambda: YamlFile.from_path(Path("b.yml")),
            None,
            'Reading `b.yml` fails with "[Errno 2]',
            id = "missing"
        ),
        param(
            "a.yml",
            "a: !custom b\n",
            lambda: YamlFile.from_path(Path("a.yml")),
            1,
            "Reading `a.yml` fails with 'could not determine a constructor",
            id = "an-unknown-tag"
        ),
        param(
            ".github/rulesets/main.json",
            '{\n"name": ,\n}\n',
            Rulesets.read,
            2,
            "Reading `.github/rulesets/main.json` fails with 'Expecting value",
            id = "json"
        ),
        param(
            "a.yml",
            "jobs:\n  a:\n    steps:\n      - run: echo it's\n",
            lambda: Workflow.from_path(Path("a.yml")),
            None,
            "Reading `a.yml` fails with 'No closing quotation'",
            id = "a-step-script"
        )
    ]
)
def test_a_file_failing_to_parse_becomes_a_finding_on_the_line_the_parser_names(
    checkout : Callable[[Mapping[str, str]], None],
    line     : int | None,
    message  : str,
    path     : str,
    read     : Callable[[], object],
    text     : str | None
):
    """
    Pins that reading a file that fails to parse raises `Unreadable` holding
    one finding on the line TOML or YAML names, and on no line for a YAML
    file holding no document or a file that is missing, the exception
    reading as the finding's message.
    """
    checkout({} if text is None else {path: text})

    with raises(Unreadable) as raised:
        read()

    [finding] = raised.value.args

    assert (finding.file, finding.line) == (Path(path), line)
    assert finding.message.startswith(message)
    assert str(raised.value) == finding.message


def test_inline_metadata_refuses_two_script_blocks():
    """
    Pins that a script carrying two `script` blocks, each closed before a
    line that is no comment, fails to read, as PEP 723 requires of a tool
    reading the metadata.
    """
    with raises(ValueError, match="more than one `script` block"):
        Metadata.from_script(
            "# /// script\n# dependencies = []\n# ///\n\n" * 2
        )


@mark.parametrize(
    ("needles", "line"),
    [
        param(("[tool.uv]", "required-version"), 4, id="a-key-under-its-table"),
        param(
            ("build-constraint-dependencies", "packaging"),
            3,
            id = "a-key-and-its-value"
        ),
        param(("[tool.uv]", "requires-python"), None, id="a-key-before-its-table"),
        param(("[tool.uv]", "required"), None, id="a-needle-inside-a-longer-name")
    ]
)
def test_a_finding_locates_each_needle_from_the_line_of_the_one_before(
    checkout : Callable[[Mapping[str, str]], None],
    line     : int | None,
    needles  : tuple[str, ...]
):
    """
    Pins that a finding sits on the first line holding the last needle at
    or after the line holding the one before it, so a key and the value it
    names may share a line, and on no line where a needle appears nowhere
    from there on or only inside a longer name.
    """
    checkout(
        {
            "pyproject.toml": (
                'requires-python = ">=3.14"\n[tool.uv]\n'
                'build-constraint-dependencies = ["packaging==26.3"]\n'
                'required-version = "==0.12.13"\n'
            )
        }
    )

    assert Finding.locate(Path("pyproject.toml"), *needles, message="x").line == line


def test_reading_several_files_reports_every_file_failing_to_parse(
    checkout: Callable[[Mapping[str, str]], None]
):
    """
    Pins that reading the workflows reads every file, the ones after a
    file failing to parse among them, and raises one `Unreadable` holding a
    finding for each failing file in the order of its path, chained to the
    group of the errors each read raised.
    """
    checkout(
        {
            ".github/workflows/a.yml" : "jobs: [\n",
            ".github/workflows/b.yml" : "jobs: {}\n",
            ".github/workflows/c.yml" : "jobs: [\n"
        }
    )

    with raises(Unreadable) as raised:
        Workflow.matching("*.yml")

    assert [finding.file for finding in raised.value.args] == [
        Path(".github/workflows/a.yml"),
        Path(".github/workflows/c.yml")
    ]
    assert isinstance(raised.value.__cause__, ExceptionGroup)
    assert len(raised.value.__cause__.exceptions) == 2


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


@mark.parametrize(
    ("text", "metadata"),
    [
        param("print(1)\n", None, id="none"),
        param(
            (
                "# /// script\n# dependencies = []\n#\n"
                "# requires-python = '>=3.14'\n# ///\n"
            ),
            {"requires_python": ">=3.14", "dependencies": []},
            id = "one"
        ),
        param(
            "# /// tool\n# x = 1\n# ///\n\n# /// script\n# dependencies = []\n# ///\n",
            {"requires_python": None, "dependencies": []},
            id = "beside-another-type"
        )
    ]
)
def test_inline_metadata_reads_the_script_block_pep_723_sets_out(
    metadata : dict[str, object] | None,
    text     : str
):
    """
    Pins that a script's inline metadata reads its `script` block through
    the pattern PEP 723 gives, keeping a bare `#` line, leaving a block of
    another type aside, and reading nothing from a script carrying none.
    """
    read = Metadata.from_script(text)

    assert (read and {
        "dependencies"    : [str(pin) for pin in read.dependencies],
        "requires_python" : read.requires_python and str(read.requires_python)
    }) == metadata


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

    with raises(Unreadable):
        Labels.read()


@mark.parametrize(
    ("on", "triggers", "pushed"),
    [
        param("", {}, False, id="none"),
        param("on: push", {"push": False}, True, id="one-name"),
        param(
            "on: [pull_request, workflow_dispatch]",
            {"pull_request": False, "workflow_dispatch": False},
            False,
            id = "a-list"
        ),
        param(
            "on:\n  push:\n    paths: [a/*.toml]",
            {"push": True},
            True,
            id = "a-filter-matching"
        ),
        param(
            "on:\n  push:\n    paths: [b/**]",
            {"push": True},
            False,
            id = "a-filter-missing"
        ),
        param(
            "on:\n  push:\n    paths: a/x.toml",
            {"push": True},
            False,
            id = "a-filter-as-one-string"
        )
    ]
)
def test_a_workflow_reads_its_triggers_in_each_form_on_takes(
    checkout : Callable[[Mapping[str, str]], None],
    on       : str,
    pushed   : bool,
    triggers : dict[str, bool]
):
    """
    Pins that a workflow reads its triggers whether `on` names one event, a
    list, or a mapping, keeping the key `on` that YAML 1.1 reads as `True`
    and holding a configuration only for an event the mapping configures,
    and that a push touching `a/x.toml` runs it unless it runs on no push or
    filters the push to other paths, a filter written as one string listing
    no pattern.
    """
    checkout({"ci.yml": f"{on}\njobs: {{}}\n"})
    workflow = Workflow.from_path(Path("ci.yml"))

    assert {
        name: event is not None for name, event in workflow.triggers.items()
    } == triggers
    assert workflow.pushes(Path("a/x.toml")) is pushed


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


def test_the_settings_leave_the_homepage_out_where_the_project_names_none(
    settings: Callable[..., Settings]
):
    """
    Pins that the request updating the repository's own fields carries no
    `homepage` where `[project.urls]` names no `Homepage`, so a homepage set
    by hand stays as it is.
    """
    assert "homepage" not in settings().plan.writes[0].body


@mark.parametrize(
    ("labels", "named"),
    [
        param("labels: 🐛 bug, 🧢 agent", ["🐛 bug", "🧢 agent"], id="a-string"),
        param("labels: [🐛 bug]", ["🐛 bug"], id="a-list"),
        param("name: Bug", [], id="none")
    ]
)
def test_a_template_reads_its_labels_from_its_frontmatter(
    checkout : Callable[[Mapping[str, str]], None],
    labels   : str,
    named    : list[str]
):
    """
    Pins that an issue template reads the labels its frontmatter sets as a
    list or as one string of names separated by commas, reading nothing of
    the Markdown below the frontmatter.
    """
    checkout({"bug.md": f"---\n{labels}\n---\n\nWhat: happened: here\n"})

    assert Template.from_path(Path("bug.md")).labels == named


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


def test_the_tasks_read_mise_s_report_even_where_validation_fails(
    checkout : Callable[[Mapping[str, str]], None],
    fp       : FakeProcess
):
    """
    Pins that the tasks read each task mise lists for the checkout and
    each defect `mise tasks validate` reports for those tasks, which
    it prints while exiting 1, and name the file declaring a task, or
    `.mise/config.toml` for a task mise did not list.
    """
    checkout({".mise/tasks/py/test": ""})
    fp.register(
        ["mise", "tasks", "ls", "--json", "--local"],
        stdout = dumps(
            [{
                "name"    : "py:test",
                "depends" : [],
                "source"  : str(Path(".mise/tasks/py/test").absolute())
            }]
        )
    )
    fp.register(
        ["mise", "tasks", "validate", "--json", "py:test"],
        returncode = 1,
        stdout     = dumps(
            {
                "errors": 1,
                "issues": [{"message": "Empty", "severity": "error", "task": "py:test"}]
            }
        )
    )
    tasks = Tasks.read()

    assert [issue.text for issue in tasks.issues] == ["'Empty'"]
    assert tasks.declaring("py:test") == Path(".mise/tasks/py/test")
    assert tasks.declaring("py:gone") == Path(".mise/config.toml")
    assert Task(
        depends = [],
        name    = "up",
        source  = Path("..").absolute() / "mise.toml"
    ).file == Path("../mise.toml")


def test_the_tasks_split_the_scripts_a_toml_task_runs(fp: FakeProcess):
    """
    Pins that the tasks split each script a task declared in TOML runs into
    its command lines, reading nothing from a step naming another task, and
    are unreadable where a script's quote never closes.
    """
    listing = [{
        "name"    : "py:x",
        "source"  : "/c.toml",
        "depends" : [],
        "run"     : []
    }]

    fp.register(["mise", "tasks", "validate", fp.any()], stdout='{"issues": []}')
    fp.register(
        ["mise", "tasks", "ls", fp.any()],
        stdout = dumps([listing[0] | {"run": ["uv run a", {"task": "py:y"}]}])
    )

    assert Tasks.read().tasks[0].runs("uv", "run") == [("a",)]

    fp.register(
        ["mise", "tasks", "ls", fp.any()],
        stdout = dumps([listing[0] | {"run": ["uv run 'a"]}])
    )

    with raises(Unreadable, match="at `0.run.0`"):
        Tasks.read()


@mark.parametrize(
    ("env", "tasks"),
    [
        param("{ TASK: py:lint }", ["py:lint"], id="a-mapping"),
        param("${{ fromJSON(needs.plan.outputs.env) }}", ["$TASK"], id="one-expression")
    ]
)
def test_a_step_reads_the_task_its_env_names(
    checkout : Callable[[Mapping[str, str]], None],
    env      : str,
    tasks    : list[str]
):
    """
    Pins that a step running `mise run "$TASK"` names the task its `env`
    gives `TASK`, and keeps the variable as written where `env` is one
    expression rather than a mapping.
    """
    checkout(
        {
            "ci.yml": (
                f"jobs:\n  a:\n    steps:\n      - env: {env}\n"
                '        run: mise run "$TASK"\n'
            )
        }
    )
    [job] = Workflow.from_path(Path("ci.yml")).jobs

    assert job.steps[0].tasks == tasks


@mark.parametrize(
    ("push", "file", "pushed"),
    [
        param("paths: ['**.js']", "src/js/app.js", True, id="a-suffix-at-any-depth"),
        param("paths: ['*.js']", "src/app.js", False, id="a-star-at-the-root"),
        param("paths: ['**/README.md']", "README.md", True, id="no-directory"),
        param("paths: ['*.jsx?']", "page.js", True, id="an-optional-character"),
        param("paths: ['docs/**', '!docs/a.md']", "docs/a.md", False, id="excluded"),
        param(
            "paths: ['!docs/a.md', 'docs/**']",
            "docs/a.md",
            True,
            id = "included-again"
        ),
        param("paths-ignore: ['docs/**']", "docs/a.md", False, id="ignored"),
        param("paths-ignore: ['docs/**']", "src/a.py", True, id="not-ignored"),
        param("paths: ['docs/a.md']", "docs/abmd", False, id="a-literal-dot"),
        param(
            "paths-ignore: ['docs/**', '*.md']",
            "docs/a.py",
            False,
            id = "ignored-by-one"
        )
    ]
)
def test_a_push_filter_reads_each_pattern_as_github_does(
    checkout : Callable[[Mapping[str, str]], None],
    file     : str,
    push     : str,
    pushed   : bool
):
    """
    Pins that a push filter matches `*` within one directory, `**`
    across directories, `**/` against none at all, and `?` as an optional
    character, lets the last pattern matching a file decide whether it
    runs the workflow, and leaves out every file a `paths-ignore` pattern
    matches.
    """
    checkout({"ci.yml": f"on:\n  push:\n    {push}\njobs: {{}}\n"})

    assert Workflow.from_path(Path("ci.yml")).pushes(Path(file)) is pushed


@mark.parametrize(
    ("run", "tasks"),
    [
        param("mise run --raw py:lint", ["py:lint"], id="a-flag-first"),
        param(
            "'mise run site:press ::: site:links'",
            ["site:press", "site:links"],
            id = "a-chain"
        ),
        param(
            "'echo \"$(mise run gha:brief)\"'",
            ["gha:brief"],
            id = "a-quoted-substitution"
        )
    ]
)
def test_a_step_names_the_task_each_mise_run_starts(
    checkout : Callable[[Mapping[str, str]], None],
    run      : str,
    tasks    : list[str]
):
    """
    Pins that a step names the task a `mise run` starts past any flag before
    it, every task of a chain it joins with `:::`, and a task inside a
    quoted command substitution.
    """
    checkout({"ci.yml": f"jobs:\n  a:\n    steps:\n      - run: {run}\n"})
    [job] = Workflow.from_path(Path("ci.yml")).jobs

    assert job.steps[0].tasks == tasks


def test_the_tree_lists_every_file_git_lists_that_the_checkout_holds(
    checkout : Callable[[Mapping[str, str]], None],
    fp       : FakeProcess
):
    """
    Pins that the tree reads git's listing of tracked and untracked files
    not ignored, in sorted order, leaving out a file git tracks that the
    working tree no longer holds, and that a failing listing is unreadable.
    """
    checkout({"a/c.toml": "", "b.py": ""})
    fp.register(
        [
            "git", "ls-files", "--cached", "--deduplicate",
            "--exclude-standard", "--others", "-z"
        ],
        stdout = "b.py\0gone.py\0a/c.toml\0"
    )

    assert Tree.read().files == [Path("a/c.toml"), Path("b.py")]

    fp.register(["git", "ls-files", fp.any()], returncode=128)

    with raises(Unreadable, match="Reading `.` fails"):
        Tree.read()
