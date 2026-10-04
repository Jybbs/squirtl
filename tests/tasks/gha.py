"""
Pins what each `gha` task decides from its inputs, meaning the output format
`gha:lint` hands zizmor for the shell it runs in, the verdict and summary
`gha:brief` writes for the jobs a gate waited on, and which cache entries
`gha:prune` treats as replaced and how it deletes one.

The stand-in under `fixtures/` answers for `zizmor`, printing each argument
it receives on a line of its own, and the `fp` fixture pytest-subprocess
provides answers every `gh` command `gha:prune` runs, so no case starts
either program.
"""

from collections.abc   import Callable
from dataclasses       import fields
from json              import dumps
from minijinja         import TemplateError
from pathlib           import Path
from pytest            import CaptureFixture, Config, MonkeyPatch, fixture, mark, param, raises
from pytest_subprocess import FakeProcess
from runpy             import run_path
from types             import ModuleType

ATTACHED = "https://github.com/Jybbs/squirtl/actions/runs/1/artifacts/2"
LATER    = "2026-09-02T00:00:00Z"


def entry(
    key        : str,
    *,
    cache_id   : int = 1,
    created    : str = "2026-09-01T00:00:00Z",
    ref        : str = "refs/heads/main",
    size_bytes : int = 1
) -> dict:
    """
    Poses one cache entry in the shape `gh cache list --json` lists it.

    Returns:
        That entry, saved on `main` at the start of 2026-09-01 unless a case
        says otherwise.
    """
    return {
        "createdAt"   : created,
        "id"          : cache_id,
        "key"         : key,
        "ref"         : ref,
        "sizeInBytes" : size_bytes
    }


def job(result: str, outputs: dict[str, str] | None = None) -> dict:
    """
    Poses one job of a `needs` context.

    Returns:
        That job, finished with `result` and declaring `outputs`, or no
        output where none is given.
    """
    return {"outputs": outputs or {}, "result": result}


@fixture
def gate(
    load_task    : Callable[[str], ModuleType],
    monkeypatch  : MonkeyPatch,
    pytestconfig : Config
) -> Callable[..., object]:
    """
    Builds a reader of the gate `gha:brief` reads, entering the worktree
    root so the template loader finds `.github/scripts/summaries/` there.

    Returns:
        A function taking the `needs` context, a passing `check` job where
        none is given, the workflow file's stem, and any runner variable to
        set beside the defaults a push to `main` sets, which returns the
        `Brief` those variables describe.
    """
    brief = load_task(".mise/tasks/gha/brief.py").Brief

    monkeypatch.chdir(pytestconfig.rootpath)

    def read(
        needs       : dict | None = None,
        workflow    : str         = "ci",
        **variables : str
    ) -> object:
        """
        Sets the variables a gate reads and returns the `Brief` they
        describe.
        """
        defaults = {
            "COMMIT"              : "",
            "GITHUB_HEAD_REF"     : "",
            "GITHUB_REF_NAME"     : "main",
            "GITHUB_REPOSITORY"   : "Jybbs/squirtl",
            "GITHUB_SERVER_URL"   : "https://github.com",
            "GITHUB_SHA"          : "0123456789abcdef",
            "GITHUB_WORKFLOW"     : f"🕹️ {workflow}",
            "GITHUB_WORKFLOW_REF" :
                f"Jybbs/squirtl/.github/workflows/{workflow}.yml@refs/heads/main",
            "NEEDS"               : dumps(needs or {"check": job("success")})
        }

        for name, value in (defaults | variables).items():
            monkeypatch.setenv(name, value)

        return brief.from_environment()

    return read


@fixture
def prune(load_task: Callable[[str], ModuleType]) -> ModuleType:
    """
    Loads the `gha:prune` task script.
    """
    return load_task(".mise/tasks/gha/prune.py")


@fixture
def templates(monkeypatch: MonkeyPatch, tmp_path: Path) -> Callable[..., None]:
    """
    Builds a writer of the templates a case poses, which writes each under
    `tmp_path / ".github/scripts/summaries"` as `<stem>.md.j2` and enters
    `tmp_path`, so the gate reads them in place of the worktree's.
    """
    def write(**texts: str):
        """
        Writes each of `texts` under the stem its keyword names.
        """
        summaries = tmp_path / ".github/scripts/summaries"

        summaries.mkdir(parents=True)

        for stem, text in texts.items():
            (summaries / f"{stem}.md.j2").write_text(text, encoding="utf-8")

        monkeypatch.chdir(tmp_path)

    return write


@mark.parametrize(
    ("needs", "workflow", "code", "sentence"),
    [
        param(
            {"check": job("success")},
            "ci",
            0,
            "## 🕹️ ci\n\n✅ Every job passed at [`0123456`]",
            id = "ci-passed"
        ),
        param(
            {"check": job("failure")},
            "ci",
            1,
            "❌ A job did not pass at [`0123456`]",
            id = "ci-failed"
        ),
        param(
            {"check": job("cancelled")},
            "ci",
            1,
            "❌ A job did not pass",
            id = "ci-cancelled"
        ),
        param(
            {"kit": job("success"), "prune": job("success")},
            "warm",
            0,
            "## 🕹️ warm\n\n✅ Every job passed",
            id = "warm-passed"
        ),
        param(
            {"kit": job("failure"), "prune": job("skipped")},
            "warm",
            1,
            "❌ A job did not pass",
            id = "warm-kit-failed"
        )
    ]
)
def test_the_gate_exits_with_the_verdict_of_every_job_it_waited_on(
    capsys   : CaptureFixture[str],
    code     : int,
    gate     : Callable[..., object],
    needs    : dict,
    sentence : str,
    workflow : str
):
    """
    Pins that the gate exits 0 only where every job it waited on succeeded,
    a cancelled or skipped job counting as one that did not, and that the
    summary opens on the workflow's name and the sentence for that verdict.
    """
    assert gate(needs, workflow).write() == code
    assert sentence in capsys.readouterr().out


@mark.parametrize(
    ("outputs", "closing"),
    [
        param(
            {"coverage": ATTACHED},
            f"The workflow run attached [`coverage`]({ATTACHED}).\n",
            id = "attached"
        ),
        param(
            {"coverage": ATTACHED, "site-coverage": f"{ATTACHED}0"},
            f"The workflow run attached [`coverage`]({ATTACHED}), "
            f"[`site-coverage`]({ATTACHED}0).\n",
            id = "two-reports"
        ),
        param({"coverage": ""}, "on `main`.\n", id="left-empty"),
        param({"artifact": ATTACHED}, "on `main`.\n", id="not-a-report")
    ]
)
def test_the_summary_links_each_coverage_report_the_run_attached(
    capsys  : CaptureFixture[str],
    closing : str,
    gate    : Callable[..., object],
    outputs : dict[str, str]
):
    """
    Pins that the summary links each job output named for a coverage report,
    in the order of their names, and leaves out one a job left empty, as
    every row of a matrix but the one attaching the report leaves it, and an
    output naming something else.
    """
    gate({"check": job("success", outputs)}).write()

    assert capsys.readouterr().out.endswith(closing)


@mark.parametrize(
    ("variables", "sentence"),
    [
        param(
            {
                "COMMIT"          : "fedcba9876543210",
                "GITHUB_HEAD_REF" : "4/ci-rows",
                "GITHUB_REF_NAME" : "19/merge"
            },
            "at [`fedcba9`](https://github.com/Jybbs/squirtl/commit/fedcba9876543210) "
            "on `4/ci-rows`.",
            id = "pull-request"
        ),
        param(
            {},
            "at [`0123456`](https://github.com/Jybbs/squirtl/commit/0123456789abcdef) "
            "on `main`.",
            id = "push"
        )
    ]
)
def test_the_summary_names_the_head_of_the_branch_it_ran_for(
    capsys    : CaptureFixture[str],
    gate      : Callable[..., object],
    sentence  : str,
    variables : dict[str, str]
):
    """
    Pins that a pull request's summary names the head of its branch, which
    the workflow sets as `COMMIT`, and the branch itself, rather than the
    merge commit and the merge ref the runner checks out, while a push names
    `GITHUB_SHA` and the branch it pushed to.
    """
    gate(**variables).write()

    assert sentence in capsys.readouterr().out


def test_a_failed_listing_stops_the_task_before_any_delete(
    fp    : FakeProcess,
    prune : ModuleType
):
    """
    Pins that a failed `gh cache list` stops the task before any delete,
    carrying the error `gh` reported as an error annotation.
    """
    fp.register(["gh", "cache", "list", fp.any()], returncode=1, stderr="HTTP 403")

    with raises(SystemExit, match="^::error::gh cache list failed, HTTP 403$"):
        prune.Caches.from_github()

    assert len(fp.calls) == 1


@mark.parametrize(
    ("workflow", "heading"),
    [param("ci", "ci's own", id="own-template"), param("warm", "base", id="base")]
)
def test_a_workflow_template_takes_precedence_over_the_base(
    capsys    : CaptureFixture[str],
    gate      : Callable[..., object],
    heading   : str,
    templates : Callable[..., None],
    workflow  : str
):
    """
    Pins that the gate fills in the template named for the running
    workflow's file where `.github/scripts/summaries/` holds one, and
    `base.md.j2` where it holds none.
    """
    templates(base="base\n", ci="ci's own\n")
    gate(workflow=workflow).write()

    assert capsys.readouterr().out == f"{heading}\n"


@mark.parametrize(
    ("listing", "replaced"),
    [
        param(
            [entry("mise-v1-zizmor-aaa"), entry("mise-v1-zizmor-bbb", created=LATER)],
            ["mise-v1-zizmor-aaa"],
            id = "older-replaced"
        ),
        param(
            [entry("mise-v1-zizmor-bbb", created=LATER), entry("mise-v1-zizmor-aaa")],
            ["mise-v1-zizmor-aaa"],
            id = "listing-order"
        ),
        param(
            [
                entry("mise-v1-zizmor-aaa"),
                entry("mise-v1-zizmor-bbb", created=LATER),
                entry("mise-v1-zizmor-ccc", created="2026-09-03T00:00:00Z")
            ],
            ["mise-v1-zizmor-aaa", "mise-v1-zizmor-bbb"],
            id = "all-but-the-newest"
        ),
        param(
            [
                entry("mise-v1-zizmor-aaa"),
                entry("mise-v1-python-uv-bbb", created=LATER),
                entry("mise-v1-zizmor-ccc", created="2026-09-03T00:00:00Z"),
                entry("mise-v1-python-uv-ddd", created="2026-09-04T00:00:00Z")
            ],
            ["mise-v1-zizmor-aaa", "mise-v1-python-uv-bbb"],
            id = "interleaved-generations"
        ),
        param(
            [
                entry("mise-v1-zizmor-aaa", created="2026-09-01T00:00:00.5Z"),
                entry("mise-v1-zizmor-bbb")
            ],
            ["mise-v1-zizmor-bbb"],
            id = "fraction-of-a-second"
        ),
        param(
            [
                entry("mise-v1-zizmor-aaa"),
                entry("mise-v1-zizmor-bbb", created=LATER, ref="refs/heads/4/ci-rows")
            ],
            [],
            id = "two-refs"
        ),
        param(
            [
                entry("mise-v1-linux-x64-2026.9.18-aaa"),
                entry("mise-v1-linux-x64-2026.10.0-bbb", created=LATER)
            ],
            [],
            id = "new-mise-release"
        ),
        param(
            [entry("hashless"), entry("hashless", created=LATER)],
            [],
            id = "no-generation"
        ),
        param([], [], id="empty")
    ]
)
def test_replaced_sets_aside_all_but_the_newest_entry_of_each_generation(
    listing  : list[dict],
    prune    : ModuleType,
    replaced : list[str]
):
    """
    Pins which entries `Caches.replaced` returns, in the order the listing
    holds them, keeping the entry each generation created last whatever
    the listing's order or the text of its timestamp, keeping the entries
    two refs or two mise releases saved apart, and never returning an entry
    whose key holds no `-`.
    """
    entries = [prune.Entry(**each) for each in listing]

    assert [each.key for each in prune.Caches(entries).replaced] == replaced


@mark.parametrize(
    ("code", "accepted", "printed"),
    [
        param(0, True, "mise-v1-zizmor-aaa deleted, 11 bytes", id="accepted"),
        param(
            1,
            False,
            "::warning::mise-v1-zizmor-aaa not deleted, HTTP 404: no such cache",
            id = "refused"
        )
    ]
)
def test_delete_reports_whether_github_accepted_it(
    accepted : bool,
    capsys   : CaptureFixture[str],
    code     : int,
    fp       : FakeProcess,
    printed  : str,
    prune    : ModuleType
):
    """
    Pins that deleting an entry runs `gh cache delete` on that entry's
    id alone, returns whether GitHub accepted the request, and prints the
    result, carrying the error `gh` reported where GitHub refused it.
    """
    fp.register(
        ["gh", "cache", "delete", "7"],
        returncode = code,
        stderr     = "HTTP 404: no such cache"
    )

    assert prune.Entry(
        **entry("mise-v1-zizmor-aaa", cache_id=7, size_bytes=11)
    ).delete() is accepted
    assert printed in capsys.readouterr().out
    assert list(fp.calls) == [["gh", "cache", "delete", "7"]]


def test_a_template_naming_an_unknown_variable_fails_the_gate(
    gate      : Callable[..., object],
    templates : Callable[..., None]
):
    """
    Pins that a template naming a variable the gate does not pass raises
    rather than rendering it as empty text, so a misspelled name fails the
    gate instead of writing a summary with a gap in it.
    """
    templates(base="{{ verdict }}\n")

    with raises(TemplateError):
        gate().write()


def test_running_the_task_lists_every_field_and_deletes_only_replaced_entries(
    capsys       : CaptureFixture[str],
    fp           : FakeProcess,
    pytestconfig : Config
):
    """
    Pins that running the task asks `gh cache list` for every field `Entry`
    declares and for up to 100 entries rather than the 30 it returns
    by default, deletes only the entry a newer entry of its generation
    replaced, and prints how many entries it deleted and how many bytes
    that freed.
    """
    listing = [
        entry("mise-v1-zizmor-aaa", size_bytes=5),
        entry("mise-v1-zizmor-bbb", cache_id=2, created=LATER)
    ]

    fp.register(["gh", "cache", "list", fp.any()], stdout=dumps(listing))
    fp.register(["gh", "cache", "delete", "1"])

    script = run_path(
        str(pytestconfig.rootpath / ".mise/tasks/gha/prune.py"),
        run_name = "__main__"
    )
    assert list(fp.calls) == [
        [
            "gh", "cache", "list", "--json",
            ",".join(field.name for field in fields(script["Entry"])),
            "--limit", "100"
        ],
        ["gh", "cache", "delete", "1"]
    ]
    assert capsys.readouterr().out.endswith(
        "1 of 1 replaced entries deleted, 5 bytes freed\n"
    )


def test_the_closing_line_counts_only_the_deletes_github_accepted(
    capsys : CaptureFixture[str],
    fp     : FakeProcess,
    prune  : ModuleType
):
    """
    Pins that the closing line counts only the deletes GitHub accepted, so a
    refused delete frees no bytes.
    """
    fp.register(["gh", "cache", "delete", "1"], returncode=1, stderr="HTTP 404")
    prune.Caches(
        [
            prune.Entry(**entry("mise-v1-zizmor-aaa", size_bytes=5)),
            prune.Entry(
                **entry(
                    cache_id = 2,
                    created  = LATER,
                    key      = "mise-v1-zizmor-bbb"
                )
            )
        ]
    ).prune()

    assert capsys.readouterr().out.endswith(
        "0 of 1 replaced entries deleted, 0 bytes freed\n"
    )


@mark.parametrize(
    ("shell", "kind"),
    [
        param({}, "plain", id="local"),
        param({"GITHUB_ACTIONS": "true"}, "github", id="actions")
    ],
    indirect = ["shell"]
)
def test_lint_hands_zizmor_the_format_its_shell_reads(
    install_stand_ins : Callable[..., Path],
    kind              : str,
    printed           : Callable[..., list[str]],
    shell             : dict[str, str]
):
    """
    Pins that `gha:lint` asks zizmor for annotations under GitHub Actions
    and for plain diagnostics elsewhere, offline and failing on a file it
    cannot collect, over every workflow and action under `.github`.
    """
    install_stand_ins("echo.sh", "zizmor")

    assert printed("gha/lint") == [
        "--format", kind, "--offline", "--strict-collection", ".github"
    ]


def test_the_summary_appends_to_the_step_summary_file(
    capsys   : CaptureFixture[str],
    gate     : Callable[..., object],
    tmp_path : Path
):
    """
    Pins that the gate appends its summary to the file `GITHUB_STEP_SUMMARY`
    names rather than printing it, keeping whatever the file already held.
    """
    page = tmp_path / "summary.md"

    page.write_text("earlier\n", encoding="utf-8")
    gate(GITHUB_STEP_SUMMARY=str(page)).write()

    assert page.read_text(encoding="utf-8").startswith("earlier\n## 🕹️ ci\n")
    assert capsys.readouterr().out == ""
