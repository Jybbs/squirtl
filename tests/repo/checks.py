"""
Pins what each check `repo:audit` runs reports, covering:

- The pins the Python, uv, and build homes hold, and the scripts under
  `.mise/` against the lockfile and the manifest
- The license file and `CITATION.cff` against the manifest
- The workflows and the action manifests, meaning their commits, anchors,
  inputs, runners, tool subsets, push filters, gates, and the steps writing
  the summary
- The rows of a pull-request workflow against `repo:ci`, and each defect
  `mise tasks validate` reports
- The label registry against the files naming its labels
- The layout of the package and the docstrings of its Python
- How `Audit` reads every check and reports what they find

Each case writes the files it reads under `tmp_path` through the `checkout`
fixture, and hands a check the records git and mise list as records built in
memory, or answers git and mise through the `fp` fixture pytest-subprocess
provides where the audit reads them itself, so no case starts either
program.
"""

from collections.abc   import Callable, Mapping
from json              import dumps
from pathlib           import Path
from pytest            import CaptureFixture, fixture, mark, param, raises
from pytest_subprocess import FakeProcess
from textwrap          import dedent

from squirtl.emulator.schemas import Record
from squirtl.repo.checks  import (
    Anchors, Attribution, Audit, Check, Commits, Docstrings, Gates, Inputs,
    LabelCheck, Layout, Pins, Rows, Runners, ScriptCheck, Subsets, Summaries,
    TaskCheck,
    Warming
)
from squirtl.repo.schemas import Finding, Severity, Task, TaskIssue, Tasks, Tree, Unreadable

type Scan = Callable[..., list[tuple[str, int | None, str]]]


@fixture
def scan(checkout: Callable[[Mapping[str, str]], None]) -> Scan:
    """
    Builds a runner of one check over the files a case writes, which reads
    each record the check declares from those files unless the case hands it
    a record built in memory.

    Returns:
        A function taking the check, the files, and any records, which
        returns each finding as its file, its line, and its message.
    """
    def run(
        check    : type[Check],
        files    : Mapping[str, str],
        *records : Record
    ) -> list[tuple[str, int | None, str]]:
        """
        Writes `files`, then reads and scans the check.
        """
        given = {type(record): record for record in records}

        checkout({path: dedent(text) for path, text in files.items()})

        return [
            (str(finding.file), finding.line, finding.message)
            for finding in (
                check.read(lambda field: given.get(field) or field.read())
                     .scan()
            )
        ]

    return run


@fixture
def workflow() -> str:
    """
    Builds the text of a workflow that a pull request runs, holding a matrix
    row per task beside the gate every check passes.
    """
    return """
        name        : 🕹️ CI
        cache-mode  : read
        permissions : { contents: read }

        on:
          pull_request:

        jobs:
          check:
            name    : ${{ matrix.name }}
            runs-on : ubuntu-26.04

            strategy:
              matrix:
                include:
                  - name  : 🪻 Prose
                    task  : py:lint
                    tools : python uv
                  - name  : 🗝️ Workflows
                    task  : gha:lint
                    tools : zizmor

            steps:
              - uses : actions/checkout@aaa
              - uses : ./.github/actions/provision
                with : { tools: "${{ matrix.tools }}" }
              - env  : { TASK: "${{ matrix.task }}" }
                run  : mise run "$TASK"

          brief:
            name    : 🎒 Brief
            if      : always()
            needs   : check
            runs-on : ubuntu-26.04

            steps:
              - uses : ./.github/actions/provision
                with : { tools: python uv }
              - run : mise run gha:brief
        """


@fixture
def provision() -> str:
    """
    Builds the text of a composite action manifest declaring the one input
    `tools`.
    """
    return """
        name: Provision

        inputs:
          tools:
            required: true

        runs:
          using: composite

          steps:
            - uses : jdx/mise-action@ccc
              with : { install_args: "${{ inputs.tools }}" }
        """


@mark.parametrize(
    ("rewrite", "found"),
    [
        param(("", ""), [], id="clean"),
        param(
            ('requires-python = ">=3.14"', 'requires-python = ">=3.13"'),
            [
                (
                    12,
                    "`requires-python` is `>=3.13`, whereas the Python 3.14.6 "
                    "`.mise/config.toml` pins makes it `>=3.14`"
                )
            ],
            id = "requires-python"
        ),
        param(
            ('target-version = "3.14"', 'target-version = "3.13"'),
            [
                (
                    22,
                    "`target-version` is `3.13` under `[tool.prose]`, whereas the "
                    "Python 3.14.6 `.mise/config.toml` pins makes it `3.14`"
                )
            ],
            id = "target-version"
        ),
        param(
            ('"==0.12.13"', '">=0.12"'),
            [
                (
                    31,
                    "`required-version` is `>=0.12` under `[tool.uv]`, whereas the "
                    "uv 0.12.13 `.mise/config.toml` pins makes it `==0.12.13`"
                )
            ],
            id = "required-version"
        ),
        param(
            ("hatchling==1.32.4", "hatchling>=1.32"),
            [(3, "`hatchling>=1.32` under `[build-system]` pins no exact version")],
            id = "build-requirement"
        ),
        param(
            ("packaging==26.3", "packaging==26.*"),
            [
                (
                    30,
                    "`packaging==26.*` under `build-constraint-dependencies` pins "
                    "no exact version"
                )
            ],
            id = "build-constraint"
        ),
        param(
            ('requires-python = ">=3.14"', 'requires-python = ">=3.14,<3.16"'),
            [],
            id = "an-upper-bound"
        )
    ]
)
def test_pins_report_each_home_that_departs_from_the_pin(
    found    : list[tuple[int, str]],
    manifest : str,
    rewrite  : tuple[str, str],
    scan     : Scan
):
    """
    Pins that the pins check passes a manifest repeating the Python minor
    and the uv release mise pins and pinning each build package exactly, and
    reports each key that departs, on the line declaring it.
    """
    findings = scan(
        Pins,
        {
            ".mise/config.toml" : '[tools]\npython = "3.14.6"\nuv = "0.12.13"\n',
            "pyproject.toml"    : manifest.replace(*rewrite) if rewrite[0] else manifest
        }
    )

    assert [(line, message) for _, line, message in findings] == found


@mark.parametrize(
    ("path", "text", "found"),
    [
        param(
            ".mise/tasks/gha/brief.py",
            """
            #!/usr/bin/env -S uv run --exact --locked --script
            # /// script
            # dependencies    = ["minijinja==2.24.0"]
            # requires-python = ">=3.14"
            # ///
            """,
            [],
            id = "clean-script"
        ),
        param(
            ".mise/tasks/gha/brief.py",
            """
            #!/usr/bin/env -S uv run --exact --locked --script
            # /// script
            # dependencies    = ["minijinja==2.23.0", "jinja2"]
            # requires-python = ">=3.13"
            # ///
            """,
            [
                (
                    4,
                    "`.mise/tasks/gha/brief.py` declares `requires-python` as "
                    "`>=3.13`, whereas `[project]` declares `>=3.14`"
                ),
                (
                    3,
                    "`.mise/tasks/gha/brief.py` declares `minijinja==2.23.0`, "
                    "whereas `uv.lock` resolves 2.24.0"
                ),
                (
                    3,
                    "`.mise/tasks/gha/brief.py` declares `jinja2`, whereas "
                    "`uv.lock` resolves no version of it"
                )
            ],
            id = "metadata"
        ),
        param(
            ".mise/tasks/gha/brief.py",
            """
            #!/usr/bin/env -S uv run --exact --locked
            # /// script
            # dependencies = ["minijinja==2.24.0"]
            # ///
            """,
            [
                (
                    1,
                    "`.mise/tasks/gha/brief.py` declares its own dependencies, "
                    "whereas its shebang takes no `--script` after "
                    "`--exact --locked`"
                )
            ],
            id = "no-script"
        ),
        param(
            ".mise/tasks/py/test",
            """
            #!/usr/bin/env -S bash -euo pipefail
            report=$(uv run --locked pytest) && \\
              uv run --exact --locked pytest
            """,
            [(2, "`uv run` in `.mise/tasks/py/test` opens on no `--exact --locked`")],
            id = "unlocked-run"
        ),
        param(
            ".mise/bin/prose",
            """
            #!/bin/sh
            exec uv run --exact --locked --project "$root" prose "$@"
            """,
            [],
            id = "clean-wrapper"
        )
    ]
)
def test_scripts_report_their_metadata_and_every_unlocked_run(
    checkout : Callable[[Mapping[str, str]], None],
    found    : list[tuple[int, str]],
    manifest : str,
    path     : str,
    scan     : Scan,
    text     : str
):
    """
    Pins that the script check reports a script's `requires-python` and
    each dependency its inline metadata declares that the manifest or the
    lockfile does not, every `uv run` opening on anything but `--exact
    --locked`, and a shebang running a script with metadata of its own
    without `--script`.
    """
    checkout(
        {
            path             : dedent(text).lstrip("\n"),
            "pyproject.toml" : manifest,
            "uv.lock"        : '[[package]]\nname = "minijinja"\nversion = "2.24.0"\n'
        }
    )
    Path(path).chmod(0o755)

    findings = scan(ScriptCheck, {}, Tasks(issues=[], tasks=[]))

    assert [(line, message) for _, line, message in findings] == found


def test_anchors_report_each_anchor_and_alias_a_manifest_carries(scan: Scan):
    """
    Pins that the anchor check reports the line of each anchor and each
    alias in an action manifest, and nothing in a workflow carrying them.
    """
    findings = scan(
        Anchors,
        {
            ".github/actions/provision/action.yml": """
                runs:
                  steps:
                    - &first { run: echo }
                    - *first
                """,

            ".github/workflows/ci.yml":
                "jobs:\n  one: &job { runs-on: x }\n  two: *job\n"
        }
    )

    assert [line for _, line, _ in findings] == [4, 5]


@mark.parametrize(
    ("files", "found"),
    [
        param({}, [], id="clean"),
        param(
            {
                "CITATION.cff": (
                    "authors: [{ family-names: Ketchum, given-names: Ash }]\n"
                    "title: SquiRtL\n"
                ),
                "LICENSE.md": "MIT License\n\nCopyright (c) 2024-2026 Ash Ketchum\n"
            },
            [],
            id = "a-year-range-and-a-field-left-out"
        ),
        param(
            {"CITATION.cff": "authors: [{ name: Ash Ketchum }]\ntitle: SquiRtL\n"},
            [],
            id = "an-entity-author"
        ),
        param(
            {"LICENSE.md": "MIT License\n\nPermission is hereby granted.\n"},
            [
                (
                    "LICENSE.md",
                    None,
                    "The copyright line of `LICENSE.md` leaves out Ash Ketchum, "
                    "whom `[project].authors` names"
                )
            ],
            id = "no-copyright-line"
        ),
        param(
            {"LICENSE.md": "Apache License\n\nCopyright (c) 2024 Gary Oak\n"},
            [
                (
                    "LICENSE.md",
                    1,
                    "`LICENSE.md` is titled 'Apache License', whereas "
                    "`[project].license` is `MIT`"
                ),
                (
                    "LICENSE.md",
                    3,
                    "The copyright line of `LICENSE.md` leaves out Ash Ketchum, "
                    "whom `[project].authors` names"
                )
            ],
            id = "license-file"
        ),
        param(
            {
                "CITATION.cff": """
                    authors:
                      - family-names : Oak
                        given-names  : Gary
                    license : Apache-2.0
                    title   : Squirtle
                    version : 0.2.0
                    """
            },
            [
                (
                    "CITATION.cff",
                    5,
                    "`CITATION.cff` names the license 'Apache-2.0', whereas "
                    "`[project]` declares 'MIT'"
                ),
                (
                    "CITATION.cff",
                    6,
                    "`CITATION.cff` names the title 'Squirtle', whereas "
                    "`[project]` declares 'squirtl'"
                ),
                (
                    "CITATION.cff",
                    7,
                    "`CITATION.cff` names the version '0.2.0', whereas "
                    "`[project]` declares '0.1.0'"
                ),
                (
                    "CITATION.cff",
                    3,
                    "`CITATION.cff` credits Gary Oak, whom `[project].authors` "
                    "leaves out"
                ),
                (
                    "CITATION.cff",
                    2,
                    "`CITATION.cff` leaves out Ash Ketchum, whom "
                    "`[project].authors` names"
                )
            ],
            id = "citation"
        )
    ]
)
def test_attribution_reports_each_credit_the_manifest_does_not_declare(
    files    : dict[str, str],
    found    : list[tuple[str, int, str]],
    manifest : str,
    scan     : Scan
):
    """
    Pins that the attribution check passes a license file titled for the
    manifest's license and crediting its author, and a citation naming the
    package's title in any case, its version, its license, and its author,
    and reports each of them that departs, on the line it sits on.
    """
    shipped = {
        "CITATION.cff"   : """
            authors:
              - family-names : Ketchum
                given-names  : Ash
            license : MIT
            title   : SquiRtL
            version : 0.1.0
            """,
        "LICENSE.md"     : "MIT License\n\nCopyright (c) 2024 Ash Ketchum\n",
        "pyproject.toml" : manifest
    }

    assert scan(Attribution, shipped | files) == found


def test_attribution_reports_a_missing_license_file_beside_the_citation(
    manifest : str,
    scan     : Scan
):
    """
    Pins that a license file `[project].license-files` names and the
    checkout lacks becomes a finding naming it, and that the check still
    holds `CITATION.cff` to the manifest beside it.
    """
    findings = scan(
        Attribution,
        {"CITATION.cff": "title: SquiRtL\nversion: 9.9.9\n", "pyproject.toml": manifest}
    )

    assert [(file, line) for file, line, _ in findings] == [
        ("LICENSE.md", None),
        ("CITATION.cff", 2),
        ("CITATION.cff", None)
    ]
    assert findings[0][2].startswith("Reading `LICENSE.md` fails")
    assert findings[1][2] == (
        "`CITATION.cff` names the version '9.9.9', whereas `[project]` declares "
        "'0.1.0'"
    )


def test_commits_report_an_action_pinned_to_two_commits(provision: str, scan: Scan):
    """
    Pins that the commit check reports each step pinning an action that
    another step pins elsewhere, naming the other commit, and leaves alone
    an action pinned to one commit wherever it appears.
    """
    findings = scan(
        Commits,
        {
            ".github/actions/provision/action.yml": provision,

            ".github/workflows/a.yml": """
                jobs:
                  one:
                    steps:
                      - uses: actions/checkout@aaa
                      - uses: jdx/mise-action@ccc
                      - uses: ./.github/actions/provision
                      - uses: docker://alpine
                      - run: echo
                """,

            ".github/workflows/b.yml": """
                jobs:
                  two:
                    steps:
                      - uses: actions/checkout@bbb
                """
        }
    )

    assert findings == [
        (
            ".github/workflows/a.yml", 5,
            "`actions/checkout` is pinned to `aaa` here and to `bbb` elsewhere"
        ),
        (
            ".github/workflows/b.yml", 5,
            "`actions/checkout` is pinned to `bbb` here and to `aaa` elsewhere"
        )
    ]


def test_docstrings_report_each_definition_carrying_none(
    checkout : Callable[[Mapping[str, str]], None],
    scan     : Scan
):
    """
    Pins that the docstring check reports a module, a class, and a nested
    function carrying no docstring, on the line each opens on, and reports
    each file failing to parse on the line the parser names while still
    reporting the files beside it.
    """
    source = dedent(
        '''
        class Box:
            """
            A box.
            """

            def open(self):
                def lid():
                    """
                    A lid.
                    """

        async def shut():
            """
            Shuts the box.
            """

            async def latch():
                pass
        '''
    ).lstrip()

    findings = scan(
        Docstrings,
        {
            "src/squirtl/repo/box.py" : source,
            "src/squirtl/repo/lid.py" : '"""\nA lid.\n"""\n'
        },
        Tree(
            files = [
                Path("src/squirtl/repo/box.py"),
                Path("src/squirtl/repo/lid.py"),
                Path("README.md")
            ]
        )
    )

    assert findings == [
        (
            "src/squirtl/repo/box.py", 1,
            "The module `src/squirtl/repo/box.py` carries no docstring"
        ),
        (
            "src/squirtl/repo/box.py", 6,
            "`open` in `src/squirtl/repo/box.py` carries no docstring"
        ),
        (
            "src/squirtl/repo/box.py", 17,
            "`latch` in `src/squirtl/repo/box.py` carries no docstring"
        )
    ]

    broken = scan(
        Docstrings,
        {
            "src/squirtl/repo/box.py" : '"""\nA box.\n"""\n\ndef (\n',
            "src/squirtl/repo/lid.py" : "x = 1\n",
            "src/squirtl/repo/pin.py" : "def (\n"
        },
        Tree(
            files = [
                Path("src/squirtl/repo/box.py"),
                Path("src/squirtl/repo/lid.py"),
                Path("src/squirtl/repo/pin.py")
            ]
        )
    )

    assert [(file, line) for file, line, _ in broken] == [
        ("src/squirtl/repo/box.py", 5),
        ("src/squirtl/repo/lid.py", 1),
        ("src/squirtl/repo/pin.py", 1)
    ]
    assert broken[0][2].startswith("Reading `src/squirtl/repo/box.py` fails with")


def test_inputs_report_an_input_the_manifest_does_not_declare(
    provision : str,
    scan      : Scan
):
    """
    Pins that the input check reports each input a step passes an action
    of this repository that the action's manifest leaves out, on the line
    passing it, whichever prefix names the action.
    """
    findings = scan(
        Inputs,
        {
            ".github/actions/provision/action.yml" : provision,
            ".github/workflows/ci.yml"             : """
                jobs:
                  one:
                    steps:
                      - uses: $/.github/actions/provision
                        with:
                          tools  : python uv
                          caches : uv
                      - uses: ./.github/actions/provision
                        with: { tool: zizmor }
                """
        }
    )

    assert findings == [
        (
            ".github/workflows/ci.yml", 8,
            "`caches` is no input `.github/actions/provision/action.yml` declares"
        ),
        (
            ".github/workflows/ci.yml", 10,
            "`tool` is no input `.github/actions/provision/action.yml` declares"
        )
    ]


def test_labels_report_a_label_in_no_category_and_a_malformed_row(scan: Scan):
    """
    Pins that the label check reports a label no category files, and
    that a row whose color is no six lowercase hexadecimal digits raises
    `Unreadable` naming the row's field.
    """
    release = "changelog:\n  categories:\n    - { title: Other, labels: ['*'] }\n"
    row     = '[[labels]]\ncolor = "{}"\ndescription = "The agent"\nname = "🧢 agent"\n'
    findings = scan(
        LabelCheck,
        {".github/labels.toml": row.format("3aa6f0"), ".github/release.yml": release}
    )

    assert findings == [(
        ".github/labels.toml", 4, "`🧢 agent` sits in no release-notes category"
    )]

    with raises(Unreadable, match="at `labels.0.color`"):
        scan(LabelCheck, {".github/labels.toml": row.format("3AA6F0")})


def test_rows_leave_out_the_rows_of_a_workflow_no_pull_request_runs(
    scan     : Scan,
    workflow : str
):
    """
    Pins that the row check reads only the workflows a pull request runs,
    so a task a push-only workflow runs that `repo:ci` does not depend on is
    no finding.
    """
    pushed = dedent(workflow).replace("pull_request", "push")
    sweep  = Task(
        depends = ["gha:lint", "py:lint"],
        name    = "repo:ci",
        source  = Path(".mise/tasks/repo/ci").absolute()
    )

    findings = scan(
        Rows,
        {
            ".github/workflows/ci.yml"   : workflow,
            ".github/workflows/warm.yml" : pushed.replace("py:lint", "gha:prune"),
            ".mise/tasks/repo/ci"        : (
                "#!/usr/bin/env -S bash -euo pipefail\n"
                '#MISE depends = ["gha:lint", "py:lint"]\n'
            )
        },
        Tasks(issues=[], tasks=[sweep])
    )

    assert findings == []


@mark.parametrize(
    ("on", "found"),
    [
        param(
            "on:\n  push:\n    paths: [.github/**, .mise/config.toml, .mise/mise.lock]",
            [],
            id = "every-file"
        ),
        param("on:\n  push:\n    branches: [main]", [], id="no-filter"),
        param(
            "on:\n  push:\n    paths: [.github/workflows/warm.yml, .mise/*.toml]",
            [(4, ".github/actions/provision/action.yml"), (4, ".mise/mise.lock")],
            id = "two-left-out"
        ),
        param(
            "on: workflow_dispatch",
            [
                (2, ".github/actions/provision/action.yml"),
                (2, ".github/workflows/warm.yml"),
                (2, ".mise/config.toml"),
                (2, ".mise/mise.lock")
            ],
            id = "no-push"
        ),
        param(
            "on:\n  push:\n    paths-ignore: [.mise/**]",
            [(4, ".mise/config.toml"), (4, ".mise/mise.lock")],
            id = "ignored"
        )
    ]
)
def test_warming_reports_each_file_a_key_is_built_from_that_no_push_reaches(
    found     : list[tuple[int, str]],
    on        : str,
    provision : str,
    scan      : Scan
):
    """
    Pins that the warming check reports each file a cache key is built from
    that a push to the saving workflow's branches can touch without running
    it, meaning the workflow, the manifest of the action its saving job
    runs, and each file the globs `jdx/mise-action` hashes match, on the
    line of the push filter or of `on`, and nothing where a push runs the
    workflow whatever it touches.
    """
    findings = scan(
        Warming,
        {
            ".github/actions/provision/action.yml" : provision,
            ".github/workflows/warm.yml"           : (
                f"\n{on}\n\njobs:\n  kit:\n    cache-mode: write\n    steps:\n"
                "      - uses: ./.github/actions/provision\n"
                "        with: { tools: python uv }\n"
            ),
            ".mise/config.toml" : "",
            ".mise/mise.lock"   : ""
        },
        Tree(
            files = [
                Path(".mise/config.toml"),
                Path(".mise/mise.lock"),
                Path("README.md")
            ]
        )
    )

    assert findings == [
        (
            ".github/workflows/warm.yml", line,
            f"`.github/workflows/warm.yml` saves a cache keyed on `{file}`, which "
            "its push filter leaves out"
        )
        for line, file in found
    ]


@mark.parametrize(
    ("rewrite", "found"),
    [
        param(("", ""), [], id="clean"),
        param(
            ("      - run : mise run gha:brief\n", ""),
            [
                (
                    ".github/workflows/ci.yml",
                    10,
                    (
                        "`.github/workflows/ci.yml` ends on no gate, since no job runs "
                        "`gha:brief`"
                    )
                ),
                (
                    ".github/rulesets/main.json",
                    13,
                    (
                        "`main` requires the check '🎒 Brief', which no gate of a "
                        "pull-request workflow reports"
                    )
                )
            ],
            id = "no-gate"
        ),
        param(
            (
                "    name    : 🎒 Brief\n    if      : always()\n    needs   : check\n",
                ""
            ),
            [
                (
                    ".github/workflows/ci.yml", 32,
                    "The gate `brief` lacks `if: always()`, so a failed job skips it"
                ),
                (
                    ".github/workflows/ci.yml", 32,
                    "The gate `brief` sets no name, so its check reports as `brief`"
                ),
                (".github/workflows/ci.yml", 32, "The gate `brief` waits on no check"),
                (
                    ".github/rulesets/main.json",
                    13,
                    (
                        "`main` requires the check '🎒 Brief', which no gate of a "
                        "pull-request workflow reports"
                    )
                )
            ],
            id = "bare-gate"
        ),
        param(
            (
                'run  : mise run "$TASK"',
                'run  : echo done >> "$GITHUB_STEP_SUMMARY" && mise run gha:brief'
            ),
            [
                (
                    ".github/workflows/ci.yml", 11,
                    "The gate `check` lacks `if: always()`, so a failed job skips it"
                ),
                (
                    ".github/workflows/ci.yml", 11,
                    "The gate `check` is one of 2 jobs running `gha:brief`"
                ),
                (".github/workflows/ci.yml", 11, "The gate `check` waits on no brief"),
                (
                    ".github/workflows/ci.yml", 32,
                    "The gate `brief` is one of 2 jobs running `gha:brief`"
                )
            ],
            id = "two-gates"
        ),
        param(
            ("if      : always()", "if      : ${{ always() }}"),
            [],
            id = "an-expression-gate"
        )
    ]
)
def test_gates_hold_every_workflow_to_one_gate_its_ruleset_requires(
    found     : list[tuple[str, int, str]],
    provision : str,
    rewrite   : tuple[str, str],
    scan      : Scan,
    workflow  : str
):
    """
    Pins that the gate check passes a workflow ending on one named gate that
    runs `gha:brief` under `if: always()` after every other job, beside a
    ruleset requiring that gate's name, and reports each departure on the
    job it concerns, or on the ruleset for a check no gate reports.
    """
    ruleset = {
        "enforcement"   : "active",
        "name"          : "main",
        "target"        : "branch",
        "bypass_actors" : [],
        "conditions"    : {},
        "rules"         : [
            {
                "type"       : "required_status_checks",
                "parameters" : {"required_status_checks": [{"context": "🎒 Brief"}]}
            },
            {"type": "deletion"}
        ]
    }

    findings = scan(
        Gates,
        {
            ".github/actions/provision/action.yml" : provision,
            ".github/rulesets/main.json"           : dumps(
                ruleset,
                ensure_ascii = False,
                indent       = 4
            ),
            ".github/workflows/ci.yml"             : dedent(workflow).replace(*rewrite)
        }
    )

    assert findings == found


@mark.parametrize(
    ("second", "found"),
    [
        param("ubuntu-26.04", [], id="one-image"),
        param(
            "ubuntu-latest",
            [
                "`one` runs on `ubuntu-26.04`, whereas other jobs run on "
                "`ubuntu-latest`",
                "`two` runs on `ubuntu-latest`, whereas other jobs run on "
                "`ubuntu-26.04`"
            ],
            id = "two-images"
        )
    ]
)
def test_runners_report_every_job_where_two_images_run(
    found  : list[str],
    scan   : Scan,
    second : str
):
    """
    Pins that the runner check reports each job's `runs-on` once the
    workflows name two images, and nothing where every job names one,
    leaving aside a job that calls a reusable workflow and names no image.
    """
    findings = scan(
        Runners,
        {
            ".github/workflows/ci.yml": f"""
                jobs:
                  one: {{ runs-on: ubuntu-26.04 }}
                  two: {{ runs-on: {second} }}
                  three: {{ uses: ./.github/workflows/other.yml }}
                """
        }
    )

    assert [message for *_, message in findings] == found


@mark.parametrize(
    ("depends", "found"),
    [
        param(["gha:lint", "py:lint"], [], id="clean"),
        param(
            ["gha:lint"],
            [(
                ".github/workflows/ci.yml", 11,
                "A pull-request row runs `py:lint`, which `repo:ci` does not depend on"
            )],
            id = "row-outside-the-sweep"
        ),
        param(
            ["gha:lint", "py:lint", "py:coverage"],
            [(
                ".mise/tasks/repo/ci", 2,
                "`repo:ci` depends on `py:coverage`, which no pull-request row runs"
            )],
            id = "sweep-outside-the-rows"
        )
    ]
)
def test_rows_hold_the_pull_request_rows_to_the_sweep(
    depends  : list[str],
    found    : list[tuple[str, int, str]],
    scan     : Scan,
    workflow : str
):
    """
    Pins that the row check reads each task a matrix row runs through the
    variable its step sets, leaves the gate's task out, and reports each
    task the rows and `repo:ci` do not share, on the row or on the line of
    `repo:ci` declaring its dependencies.
    """
    sweep = Task(
        depends = depends,
        name    = "repo:ci",
        source  = Path(".mise/tasks/repo/ci").absolute()
    )

    findings = scan(
        Rows,
        {
            ".github/workflows/ci.yml" : workflow,
            ".mise/tasks/repo/ci"      :
                '#!/usr/bin/env -S bash -euo pipefail\n#MISE depends = ["gha:lint"]\n'
        },
        Tasks(issues=[], tasks=[sweep])
    )

    assert findings == found


def test_rows_report_a_checkout_with_no_sweep(scan: Scan, workflow: str):
    """
    Pins that the row check reports a checkout whose tasks hold no
    `repo:ci`, on `.mise/config.toml`.
    """
    findings = scan(
        Rows,
        {".github/workflows/ci.yml": workflow},
        Tasks(issues=[], tasks=[])
    )

    assert findings == [(".mise/config.toml", None, "mise lists no `repo:ci` task")]


def test_scripts_hold_a_pin_to_every_version_the_lockfile_resolves(
    checkout : Callable[[Mapping[str, str]], None],
    manifest : str,
    scan     : Scan
):
    """
    Pins that the script check matches a declared package to the lockfile's
    entries as PEP 503 normalizes their names, and reports a pin admitting
    only one of the versions a marker splits the package into.
    """
    checkout(
        {
            ".mise/tasks/gha/brief.py": (
                "#!/usr/bin/env -S uv run --exact --locked --script\n"
                "# /// script\n"
                '# dependencies = ["minijinja==2.24.0"]\n'
                "# ///\n"
            ),

            "pyproject.toml": manifest,

            "uv.lock": (
                '[[package]]\nname = "MiniJinja"\nversion = "2.23.0"\n\n'
                '[[package]]\nname = "minijinja"\nversion = "2.24.0"\n'
            )
        }
    )
    Path(".mise/tasks/gha/brief.py").chmod(0o755)

    findings = scan(ScriptCheck, {}, Tasks(issues=[], tasks=[]))

    assert [(line, message) for _, line, message in findings] == [
        (
            3,
            "`.mise/tasks/gha/brief.py` declares `minijinja==2.24.0`, whereas "
            "`uv.lock` resolves 2.23.0, 2.24.0"
        )
    ]


@mark.parametrize(
    ("files", "found"),
    [
        param({}, [], id="clean"),
        param(
            {
                ".github/labels.toml": (
                    'color       = "b8d93a"', 'color       = "3aa6f0"'
                )
            },
            [(".github/labels.toml", 3, "2 labels share the color `3aa6f0`")],
            id = "shared-color"
        ),
        param(
            {
                ".github/labels.toml": (
                    'name        = "🐛 bug"', 'name        = "🧢 agent"'
                )
            },
            [
                (".github/labels.toml", 5, "2 labels share the name `🧢 agent`"),
                (
                    ".github/release.yml",
                    4,
                    (
                        "The release-notes category '🐛 Fixes' names `🐛 bug`, which "
                        "`.github/labels.toml` does not declare"
                    )
                ),
                (
                    ".github/ISSUE_TEMPLATE/bug.md",
                    2,
                    (
                        "`.github/ISSUE_TEMPLATE/bug.md` sets `🐛 bug`, which "
                        "`.github/labels.toml` does not declare"
                    )
                )
            ],
            id = "shared-name"
        ),
        param(
            {".github/release.yml": ("labels: [🧢 agent]", "labels: [🐛 bug]")},
            [
                (
                    ".github/labels.toml", 10,
                    "`🐛 bug` sits in 2 release-notes categories rather than one"
                ),
                (
                    ".github/labels.toml", 5,
                    "`🧢 agent` sits in no release-notes category"
                )
            ],
            id = "category-counts"
        )
    ]
)
def test_labels_hold_the_registry_to_the_files_naming_its_labels(
    files : dict[str, tuple[str, str]],
    found : list[tuple[str, int, str]],
    scan  : Scan
):
    """
    Pins that the label check passes a registry whose labels each take a
    name and a color of their own and sit in one release-notes category,
    the `*` category aside, and reports a shared name or color, a label a
    category or a template names that the registry lacks, and a label in no
    category or in two.
    """
    shipped = {
        ".github/ISSUE_TEMPLATE/bug.md":
            "---\nlabels: 🐛 bug\nname: Bug\n---\n\nText.\n",

        ".github/labels.toml": """
            [[labels]]
            color       = "3aa6f0"
            description = "The agent"
            name        = "🧢 agent"

            [[labels]]
            color       = "b8d93a"
            description = "A defect"
            name        = "🐛 bug"
            """,

        ".github/release.yml": """
            changelog:
              categories:
                - { title: 🐛 Fixes, labels: [🐛 bug] }
                - { title: 🧢 Learning, labels: [🧢 agent] }
                - { title: Other, labels: ["*"] }
            """
    }

    for path, rewrite in files.items():
        shipped[path] = shipped[path].replace(*rewrite)

    assert scan(LabelCheck, shipped) == found


def test_scripts_hold_each_uv_run_a_toml_task_starts(
    checkout : Callable[[Mapping[str, str]], None],
    manifest : str,
    scan     : Scan
):
    """
    Pins that the script check reports each `uv run` a task declared in TOML
    starts that opens on anything but `--exact --locked`, on the first line
    holding one after the task's name, and reads nothing from a step naming
    another task.
    """
    checkout(
        {
            ".mise/config.toml": (
                '[tasks."py:w"]\nrun = "uv run --exact --locked w"\n\n'
                '[tasks."py:x"]\n'
                'run = ["uv run --exact --locked a", "uv run --exact b", '
                '{ task = "py:y" }]\n'
            ),
            "pyproject.toml" : manifest,
            "uv.lock"        : '[[package]]\nname = "minijinja"\nversion = "2.24.0"\n'
        }
    )
    task = Task(
        depends = [],
        name    = "py:x",
        run     = ["uv run --exact --locked a", "uv run --exact b", {"task": "py:y"}],
        source  = Path(".mise/config.toml").absolute()
    )

    assert scan(ScriptCheck, {}, Tasks(issues=[], tasks=[task])) == [
        (
            ".mise/config.toml", 5,
            "`uv run` in the task `py:x` opens on no `--exact --locked`"
        )
    ]


@mark.parametrize(
    ("files", "found"),
    [
        param(
            [
                "src/squirtl/cli/__init__.py", "src/squirtl/repo/checks.py",
                "src/squirtl/repo/notes.md", "tests/repo/checks.py"
            ],
            [],
            id = "clean"
        ),
        param(
            ["src/squirtl/main.py"],
            [
                "`src/squirtl/main.py` sits at the root of `src/squirtl`, outside "
                "every subpackage"
            ],
            id = "root-module"
        ),
        param(
            ["src/squirtl/repo/__init__.py"],
            [
                "`src/squirtl/repo/__init__.py` makes a package no entry point "
                "names, whereas every other subpackage is a namespace package"
            ],
            id = "init"
        ),
        param(
            [
                "src/squirtl/Repo/Checks.py", "src/squirtl/repo/check_.py",
                "src/squirtl/repo/utils.py"
            ],
            [
                "`Repo` in `src/squirtl/Repo/Checks.py` is not `snake_case`",
                "`Checks` in `src/squirtl/Repo/Checks.py` is not `snake_case`",
                "`check_` in `src/squirtl/repo/check_.py` is not `snake_case`",
                "`utils` in `src/squirtl/repo/utils.py` names no role a reader can find"
            ],
            id = "names"
        ),
        param(
            [
                "tests/cli/app.py", "tests/common/console.py", "tests/conftest.py",
                "tests/isolation.py", "tests/repo/fixtures/x.py", "tests/repo/pins.py",
                "tests/repo/notes.txt", "tests/tasks/repo.py"
            ],
            ["`tests/repo/pins.py` mirrors no module of the package"],
            id = "tests"
        )
    ]
)
def test_layout_reports_each_file_that_leaves_the_package_layout(
    files    : list[str],
    found    : list[str],
    manifest : str,
    scan     : Scan
):
    """
    Pins that the layout check reports a module at the root of the package,
    an `__init__.py` beside the one the command line's entry point names, a
    module or subpackage named outside `snake_case` or named `utils`, and a
    test module pytest collects that mirrors no module, leaving out the task
    tests, the command line's tests, the isolation tests, a `conftest.py`,
    and anything under a directory `norecursedirs` names.
    """
    findings = scan(
        Layout,
        {"pyproject.toml": manifest},
        Tree(files=list(map(Path, files)))
    )

    assert [message for *_, message in findings] == found


def test_scripts_skip_a_task_file_mise_would_not_run(
    checkout : Callable[[Mapping[str, str]], None],
    manifest : str,
    scan     : Scan
):
    """
    Pins that the script check reads no file under `.mise/tasks/` that
    lacks the executable bit, since mise runs no such file as a task, as the
    lockfile written beside a script with metadata of its own does.
    """
    checkout(
        {
            "pyproject.toml" : manifest,
            "uv.lock"        : '[[package]]\nname = "minijinja"\nversion = "2.24.0"\n'
        }
    )

    findings = scan(
        ScriptCheck,
        {".mise/tasks/gha/brief.py.lock": "uv run --locked pytest\n"},
        Tasks(issues=[], tasks=[])
    )

    assert findings == []


def test_subsets_report_each_subset_one_side_lacks(
    provision : str,
    scan      : Scan,
    workflow  : str
):
    """
    Pins that the subset check reports a subset a restoring job installs
    that no warming job saves and one a warming job saves that no job
    installs, comparing the tools of a subset in any order and leaving out a
    job under `cache-mode: none`.
    """
    findings = scan(
        Subsets,
        {
            ".github/actions/provision/action.yml" : provision,
            ".github/workflows/ci.yml"             : workflow,
            ".github/workflows/warm.yml"           : """
                cache-mode: write

                jobs:
                  kit:
                    strategy:
                      matrix:
                        tools: [uv python, node]

                    steps:
                      - uses : ./.github/actions/provision
                        with : { tools: "${{ matrix.tools }}" }

                  prune:
                    cache-mode: none

                    steps:
                      - uses : ./.github/actions/provision
                        with : { tools: bun }
                """
        }
    )

    assert findings == [
        (
            ".github/workflows/ci.yml", 26,
            "`check` installs the tool subset `zizmor`, which no job saves"
        ),
        (
            ".github/workflows/warm.yml", 11,
            "`kit` saves the tool subset `node`, which no job restores"
        )
    ]


@mark.parametrize(
    ("findings", "printed", "status"),
    [
        param((), "Every check passed\n", 0, id="none"),
        param(
            (Finding(
                file     = Path("a.toml"),
                line     = 3,
                message  = "Shared, 50%\nof it",
                severity = Severity.WARNING
            ),),
            "::warning file=a.toml,line=3::Shared, 50%25%0Aof it\n",
            0,
            id = "a-warning"
        ),
        param(
            (Finding(file=Path("a:b,c.toml"), message="Broken"),),
            "::error file=a%3Ab%2Cc.toml::Broken\n",
            1,
            id = "an-error"
        )
    ]
)
def test_the_audit_report_prints_each_annotation_and_fails_on_an_error(
    capsys   : CaptureFixture[str],
    findings : tuple[Finding, ...],
    printed  : str,
    status   : int
):
    """
    Pins that the report prints each finding as the workflow command GitHub
    turns into an annotation, escaping the message as data and the file as a
    property, says every check passed where nothing diverges, and exits 1 on
    an error alone.
    """
    assert Audit(findings=findings).report() == status
    assert capsys.readouterr().out == printed


@mark.parametrize(
    ("rewrites", "required", "found"),
    [
        param(
            {
                ".github/workflows/ci.yml"   : ("🎒 Brief", "🎒 Gate"),
                ".github/workflows/warm.yml" : ("pull_request", "push")
            },
            "🎒 Brief",
            [
                "`main` requires the check '🎒 Brief', which no gate of a "
                "pull-request workflow reports"
            ],
            id = "a-push-workflow-gate"
        ),
        param(
            {".github/workflows/ci.yml": ("    name    : 🎒 Brief\n", "")},
            "brief",
            ["The gate `brief` sets no name, so its check reports as `brief`"],
            id = "an-unnamed-gate"
        )
    ]
)
def test_gates_take_each_check_a_pull_request_gate_reports(
    found     : list[str],
    provision : str,
    required  : str,
    rewrites  : dict[str, tuple[str, str]],
    scan      : Scan,
    workflow  : str
):
    """
    Pins that a ruleset's required check counts as reported only by the gate
    of a workflow a pull request runs, under its name or, for a gate setting
    none, under its id, so the gate of a workflow only a push runs reports
    nothing even under the required name.
    """
    ruleset = {
        "enforcement"   : "active",
        "name"          : "main",
        "target"        : "branch",
        "bypass_actors" : [],
        "conditions"    : {},
        "rules"         : [
            {
                "type"       : "required_status_checks",
                "parameters" : {"required_status_checks": [{"context": required}]}
            }
        ]
    }

    findings = scan(
        Gates,
        {
            ".github/actions/provision/action.yml" : provision,
            ".github/rulesets/main.json"           : dumps(ruleset, ensure_ascii=False)
        }
        | {
            path: dedent(workflow).replace(*rewrites.get(path, ("", "")))
            for path in (".github/workflows/ci.yml", ".github/workflows/warm.yml")
        }
    )

    assert [message for *_, message in findings] == found


def test_summaries_report_each_writer_besides_the_gate(scan: Scan, workflow: str):
    """
    Pins that the summary check reports a step writing the summary in a
    job that runs no `gha:brief` and a step of a composite action writing
    it, and leaves alone a gate writing it beside running `gha:brief` and a
    composite step writing no summary.
    """
    text = (
        dedent(workflow).replace(
            'run  : mise run "$TASK"',
            'run  : echo done >> "$GITHUB_STEP_SUMMARY"'
        )
                        .replace(
                            "mise run gha:brief",
                            'echo x >> "$GITHUB_STEP_SUMMARY" && mise run gha:brief'
                        )
    )

    findings = scan(
        Summaries,
        {
            ".github/actions/provision/action.yml" : """
                runs:
                  steps:
                    - run: echo done >> "$GITHUB_STEP_SUMMARY"
                    - run: echo done
                """,
            ".github/workflows/ci.yml"             : text
        }
    )

    assert findings == [
        (
            ".github/workflows/ci.yml", 28,
            "`check` writes the workflow run's summary, which only the gate writes"
        ),
        (
            ".github/actions/provision/action.yml",
            4,
            "A step of `.github/actions/provision/action.yml` writes the workflow "
            "run's summary, which only a workflow's gate writes"
        )
    ]


def test_task_check_reports_each_defect_mise_finds_at_its_weight(scan: Scan):
    """
    Pins that the task check reports each defect `mise tasks validate`
    finds on the file declaring the task, an error as an error and a
    warning as a warning, and a defect in a task mise did not list on
    `.mise/config.toml`.
    """
    tasks = Tasks(
        issues = [
            TaskIssue(
                details  = "Referenced in 'depends'",
                message  = "Dependency 'x' not found",
                severity = Severity.ERROR,
                task     = "py:test"
            ),
            TaskIssue(message="Empty script", severity=Severity.WARNING, task="py:gone")
        ],
        tasks = [Task(
            depends = ["x"],
            name    = "py:test",
            source  = Path(".mise/tasks/py/test").absolute()
        )]
    )

    assert [
        (str(finding.file), finding.severity, finding.message)
        for finding in TaskCheck.read(lambda field: tasks).scan()
    ] == [
        (
            ".mise/tasks/py/test",
            Severity.ERROR,
            (
                "`py:test` fails `mise tasks validate` with \"Dependency 'x' not "
                "found\" (Referenced in 'depends')"
            )
        ),
        (
            ".mise/config.toml", Severity.WARNING,
            "`py:gone` fails `mise tasks validate` with 'Empty script'"
        )
    ]


def test_the_audit_reports_each_unreadable_file_once(
    capsys   : CaptureFixture[str],
    checkout : Callable[[Mapping[str, str]], None],
    fp       : FakeProcess
):
    """
    Pins that the audit runs every check over a checkout holding two modules
    alone, reports each file a check cannot read once however many checks
    read it, the files a check reads after one it cannot read among them,
    keeps the docstring finding beside the module that fails to parse,
    prints each as an annotation, and exits 1.
    """
    checkout({"a.py": "x = 1\n", "b.py": "def (\n"})
    fp.register(["git", "ls-files", fp.any()], stdout="a.py\0b.py\0")
    fp.register(["mise", "tasks", "ls", fp.any()], stdout="[]")
    fp.register(["mise", "tasks", "validate", fp.any()], stdout='{"issues": []}')

    audit = Audit.read()

    assert sorted({str(finding.file) for finding in audit.findings}) == [
        ".github/labels.toml", ".github/release.yml", ".mise/config.toml",
        "CITATION.cff", "a.py", "b.py",
        "pyproject.toml", "uv.lock"
    ]
    assert len(audit.findings) == len(set(audit.findings))
    assert audit.report() == 1
    assert capsys.readouterr().out.splitlines()[0].startswith(
        "::error file=CITATION.cff::"
    )


def test_warming_reads_no_workflow_that_saves_no_cache(
    provision : str,
    scan      : Scan,
    workflow  : str
):
    """
    Pins that the warming check holds no push filter to a cache's key where
    the workflow's jobs only restore caches, even a workflow no push runs.
    """
    findings = scan(
        Warming,
        {
            ".github/actions/provision/action.yml" : provision,
            ".github/workflows/ci.yml"             : workflow,
            ".mise/config.toml": ""
        },
        Tree(files=[Path(".mise/config.toml")])
    )

    assert findings == []
