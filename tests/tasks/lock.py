"""
Pins what the `lock:check` task decides and prints from what `uv lock
--check`, `mise lock --check`, the dry run of `mise lock`, the locked
dry-run install, Bun's frozen dry-run install, and `lock:advisories` report,
which lockfiles `lock:sync` re-resolves, and which advisories `mise audit`
reports that `lock:advisories` passes.

Each case runs its task from `tmp_path`, which holds placeholder task
scripts wherever the case reaches their lockfiles. The stand-in under
`fixtures/` answers for `bun`, `mise`, and `uv` in every case, writing each
call it receives to a file and printing the `[]` the dry run of `mise lock`
prints on a lockfile naming no tool the config dropped, unless the case sets
another answer, so no case reaches the network.
"""

from collections.abc import Callable
from json            import dumps
from pathlib         import Path
from pytest          import Config, MonkeyPatch, fixture, mark, param
from subprocess      import CompletedProcess, run

ADVISORIES = "mise run lock:advisories"
BUN        = "bun install --cwd docs --dry-run --frozen-lockfile"
CHECK      = "mise lock --check"
DRY_RUN    = "mise lock --dry-run --json --quiet"
INSTALL    = "mise install --dry-run --force"
UV         = "uv lock --check"


@fixture
def calls(stand_ins: Path) -> Callable[[], list[str]]:
    """
    Builds a reader of the calls the stand-in wrote, one line each.
    """
    return lambda: stand_ins.read_text(encoding="utf-8").splitlines()


@fixture
def checked(
    pytestconfig : Config,
    tmp_path     : Path
) -> Callable[[], CompletedProcess[str]]:
    """
    Builds a runner of the worktree's `lock:check` task that starts it from
    `tmp_path`, capturing what it prints.
    """
    task = pytestconfig.rootpath / ".mise/tasks/lock/check"

    return lambda: run([task], capture_output=True, cwd=tmp_path, text=True)


@fixture
def scripts(tmp_path: Path) -> str:
    """
    Writes two placeholder task scripts under `tmp_path / ".mise/tasks"`,
    one declaring its own dependencies through inline metadata and one
    carrying none, so a case reads which of them a task locks.

    Returns:
        The path of the script declaring its dependencies, relative to
        `tmp_path`, as the task names it.
    """
    tasks = tmp_path / ".mise/tasks/gha"

    tasks.mkdir(parents=True)
    (tasks / "brief.py").write_text("# /// script\n# ///\n", encoding="utf-8")
    (tasks / "prune.py").write_text("print()\n", encoding="utf-8")

    return ".mise/tasks/gha/brief.py"


@fixture(autouse=True)
def stand_ins(
    install_stand_ins : Callable[..., Path],
    monkeypatch       : MonkeyPatch,
    pytestconfig      : Config,
    tmp_path          : Path
) -> Path:
    """
    Puts the stand-in ahead of the real `bun`, `mise`, and `uv` on the path
    for every case, under each of their names, so no case reaches any of
    them, sets the stand-in to answer each call with `[]`, and sets the
    `MISE_PROJECT_ROOT` both tasks source `.mise/lib/lock.sh` through.

    The stand-in exits 1 where its call matches the shell pattern `FAILING`
    holds.

    Returns:
        The file the stand-in writes each call it receives to.
    """
    received = tmp_path / "calls"

    install_stand_ins("stand-in.sh", "bun", "mise", "uv")
    monkeypatch.setenv("ANSWER", "[]")
    monkeypatch.setenv("CALLS", str(received))
    monkeypatch.setenv("MISE_PROJECT_ROOT", str(pytestconfig.rootpath))

    return received


@mark.parametrize(
    ("failing", "reached"),
    [
        param(UV, [UV], id="lagging-uv-lock"),
        param(
            CHECK,
            [UV, CHECK],
            id = "request-missing-from-the-lockfile"
        ),
        param(
            DRY_RUN,
            [UV, CHECK, DRY_RUN],
            id = "unresolvable-dry-run"
        ),
        param(
            "*mise install*",
            [UV, CHECK, DRY_RUN, INSTALL],
            id = "tool-missing-from-the-lockfile"
        ),
        param(
            "bun install*",
            [UV, CHECK, DRY_RUN, INSTALL, BUN],
            id = "lagging-bun-lockfile"
        ),
        param(
            ADVISORIES,
            [UV, CHECK, DRY_RUN, INSTALL, BUN, ADVISORIES],
            id = "advisory-against-a-pinned-tool"
        )
    ]
)
def test_a_failing_step_fails_the_task_running_no_step_after_it(
    calls       : Callable[[], list[str]],
    checked     : Callable[[], CompletedProcess[str]],
    failing     : str,
    monkeypatch : MonkeyPatch,
    reached     : list[str]
):
    """
    Pins that the task exits 1 once a step exits 1, as `uv lock --check`
    does on a `uv.lock` lagging `pyproject.toml`, `mise lock --check` does
    on a request `.mise/mise.lock` holds no version for, the dry run of
    `mise lock` does where it cannot resolve a tool, the locked dry-run
    install does on a pinned tool with no entry the running platform
    installs from, Bun's frozen dry-run install does on a `docs/bun.lock`
    lagging `docs/package.json`, and `lock:advisories`, the last step, does
    on an advisory against a pinned tool, and runs no step after it.
    """
    monkeypatch.setenv("FAILING", failing)

    assert checked().returncode == 1
    assert calls() == reached


def advisory(*fixed: str) -> dict[str, object]:
    """
    Builds an advisory against `python` 3.15.2 as `mise audit --json` lists
    it, fixed in each of `fixed`.
    """
    return {
        "id"       : "CVE-2026-0001",
        "fixed"    : list(fixed),
        "severity" : None,
        "summary"  : "A stand-in advisory",
        "tool"     : "python",
        "url"      : "https://osv.dev/vulnerability/CVE-2026-0001",
        "version"  : "3.15.2",
        "aliases"  : ["GHSA-0000-0000-0001"]
    }


def test_a_failed_audit_stops_the_task(
    audited     : Callable[..., CompletedProcess[str]],
    monkeypatch : MonkeyPatch
):
    """
    Pins that the task exits 1 where `mise audit` fails printing no report,
    as it does without the network, rather than reading an empty report as
    a pass.
    """
    monkeypatch.setenv("FAILING", "mise audit*")

    result = audited()

    assert result.returncode == 1
    assert result.stderr == "mise audit printed no report\n"


@mark.parametrize(
    ("failing", "code", "reached"),
    [
        param("", 0, [CHECK, DRY_RUN, INSTALL, BUN, ADVISORIES], id="current"),
        param(f"{UV} --script*", 1, [], id="stale")
    ]
)
def test_each_task_script_lockfile_is_checked_before_mise_lock(
    calls       : Callable[[], list[str]],
    checked     : Callable[[], CompletedProcess[str]],
    code        : int,
    failing     : str,
    monkeypatch : MonkeyPatch,
    reached     : list[str],
    scripts     : str
):
    """
    Pins that the task checks the lockfile beside each task script declaring
    its own dependencies, and no other script, between `uv lock --check`
    and `mise lock --check`, and exits 1 without running `mise lock --check`
    once one lags its script.
    """
    monkeypatch.setenv("FAILING", failing)

    assert checked().returncode == code
    assert calls() == [
        UV,
        f"{UV} --script {scripts}",
        *reached
    ]


def test_a_locked_tool_the_config_dropped_fails_the_task(
    calls       : Callable[[], list[str]],
    checked     : Callable[[], CompletedProcess[str]],
    monkeypatch : MonkeyPatch
):
    """
    Pins that the task exits 1, prints the dry run's report, and runs
    no step after it when the dry run of `mise lock` lists a change,
    as it lists with no new versions a tool `.mise/mise.lock` holds and
    `.mise/config.toml` no longer declares, which `mise lock --check`
    passes.
    """
    report = (
        '[{"name": "jq", "backend": "aqua:jqlang/jq", "old_versions": ["1.8.1"],'
        ' "new_versions": []}]'
    )
    monkeypatch.setenv("ANSWER", report)

    result = checked()

    assert result.returncode == 1
    assert report in result.stderr
    assert calls() == [UV, CHECK, DRY_RUN]


@fixture
def audited(
    monkeypatch  : MonkeyPatch,
    pytestconfig : Config,
    tmp_path     : Path
) -> Callable[..., CompletedProcess[str]]:
    """
    Builds a runner of the worktree's `lock:advisories` task over a project
    under `tmp_path` pinning `node` and `python`, whose stand-in `mise
    audit` reports each advisory the runner receives.

    Returns:
        A function taking the advisories as the mappings `mise audit
        --json` lists, and the ids `AUDIT_IGNORE` lists as keywords, which
        returns what the task printed.
    """
    config = tmp_path / ".mise/config.toml"

    config.parent.mkdir()
    config.write_text(
        '[tools]\nnode = "26.13.1"\npython = "3.15.2"\n',
        encoding = "utf-8"
    )
    monkeypatch.setenv("MISE_PROJECT_ROOT", str(tmp_path))

    def audit(
        *advisories : dict[str, object],
        ignored     : str = ""
    ) -> CompletedProcess[str]:
        """
        Starts the task with `advisories` as the audit's report and
        `ignored` as `AUDIT_IGNORE`.
        """
        monkeypatch.setenv(
            "ANSWER",
            dumps({"vulnerabilities": advisories, "unchecked": []})
        )
        monkeypatch.setenv("AUDIT_IGNORE", ignored)

        return run(
            [pytestconfig.rootpath / ".mise/tasks/lock/advisories.py"],
            capture_output = True,
            cwd            = tmp_path,
            text           = True
        )

    return audit


def test_a_lockfile_in_step_with_its_pins_passes(
    calls   : Callable[[], list[str]],
    checked : Callable[[], CompletedProcess[str]]
):
    """
    Pins that the task exits 0 once `uv lock --check` and `mise lock
    --check` pass, the dry run of `mise lock` lists no change, the dry-run
    install finds every tool the project pins, Bun finds `docs/bun.lock`
    current, and `lock:advisories` passes, running the six in that order and
    printing what each step but the two runs of `mise lock` answers.
    """
    result = checked()

    assert result.returncode == 0
    assert calls() == [UV, CHECK, DRY_RUN, INSTALL, BUN, ADVISORIES]
    assert result.stdout.splitlines() == ["[]"] * 4


def test_each_advisory_in_one_report_is_judged_on_its_own(
    audited: Callable[..., CompletedProcess[str]]
):
    """
    Pins that the task prints only the advisory `AUDIT_IGNORE` leaves out
    where the report also holds one the list passes, and still exits 1.
    """
    result = audited(
        advisory(),
        {
            **advisory(),
            "id"      : "CVE-2026-0002",
            "tool"    : "node",
            "aliases" : []
        },
        ignored = "CVE-2026-0001"
    )

    assert result.returncode == 1
    assert result.stderr == "CVE-2026-0002 affects node 3.15.2: A stand-in advisory\n"


@mark.parametrize(
    ("found", "ignored", "code", "printed"),
    [
        param(advisory(), "CVE-2026-0001", 0, "", id="ignored-with-no-fix"),
        param(
            advisory(),
            "GHSA-0000-0000-0001",
            0,
            "",
            id = "ignored-by-alias-with-no-fix"
        ),
        param(
            advisory("3.15.3", "3.16.0"),
            "CVE-2026-0001",
            1,
            (
                "CVE-2026-0001 is fixed in 3.15.3, 3.16.0, so delete "
                "CVE-2026-0001 from AUDIT_IGNORE in .mise/config.toml and lift "
                "python 3.15.2 to a fixed version\n"
            ),
            id = "ignored-with-a-fix"
        ),
        param(
            advisory("3.15.3"),
            "GHSA-0000-0000-0001",
            1,
            (
                "CVE-2026-0001 is fixed in 3.15.3, so delete GHSA-0000-0000-0001 "
                "from AUDIT_IGNORE in .mise/config.toml and lift python 3.15.2 "
                "to a fixed version\n"
            ),
            id = "ignored-by-alias-with-a-fix"
        ),
        param(
            advisory(),
            "CVE-2026-0002",
            1,
            "CVE-2026-0001 affects python 3.15.2: A stand-in advisory\n",
            id = "unlisted-with-no-fix"
        ),
        param(
            advisory("3.15.3"),
            "",
            1,
            (
                "CVE-2026-0001 affects python 3.15.2, fixed in 3.15.3: "
                "A stand-in advisory\n"
            ),
            id = "unlisted-with-a-fix"
        )
    ]
)
def test_an_ignored_advisory_passes_only_while_no_release_fixes_it(
    audited : Callable[..., CompletedProcess[str]],
    code    : int,
    found   : dict[str, object],
    ignored : str,
    printed : str
):
    """
    Pins that the task passes an advisory `AUDIT_IGNORE` lists by its id
    or an alias while it names no fixed version, and fails on a listed one
    naming a fix, saying which advisory, tool, and versions, and on any
    advisory the list leaves out.
    """
    result = audited(found, ignored=ignored)

    assert result.returncode == code
    assert result.stderr == printed


def test_relock_re_resolves_every_lockfile(
    calls        : Callable[[], list[str]],
    pytestconfig : Config,
    scripts      : str,
    tmp_path     : Path
):
    """
    Pins that `lock:sync` re-resolves `.mise/mise.lock`, then `uv.lock`,
    then the lockfile beside each task script declaring its own
    dependencies, the two uv calls lifting the `UV_LOCKED` the `[env]` block
    sets, then `docs/bun.lock`, which Bun writes without installing.
    """
    run([pytestconfig.rootpath / ".mise/tasks/lock/sync"], check=True, cwd=tmp_path)

    assert calls() == [
        "mise lock", "uv lock --no-locked",
        f"uv lock --no-locked --script {scripts}",
        "bun install --cwd docs --lockfile-only"
    ]


def test_the_audit_reads_only_the_tools_the_project_pins(
    audited : Callable[..., CompletedProcess[str]],
    calls   : Callable[[], list[str]]
):
    """
    Pins that the task names each tool `[tools]` in `.mise/config.toml` pins
    to `mise audit`, so a tool a global mise config adds stays out of the
    report, and passes where the audit reports no advisory.
    """
    result = audited()

    assert result.returncode == 0
    assert result.stderr == ""
    assert calls() == ["mise audit --json --quiet node python"]
