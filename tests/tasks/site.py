"""
Pins what the `site` tasks decide from the shell and the checkout they run
in, meaning the output format `site:lint` chooses for the shell it runs in,
the ref `site:affected` hands Vitest's `--changed`, each further argument
the tasks forward after their own flags, and the single-file component
`site:typecheck` refuses before `tsc` starts, and that `site:lint` runs its
line check after Oxlint whatever Oxlint returns.

Each case runs its task from `tmp_path`, where the links under
`node_modules/.bin/` and the `node` first on the path lead to the stand-in
under `fixtures/`, which prints each argument it receives on a line of its
own, so no case starts Oxlint, `tsc`, or Vitest, and only the line check's
own case starts Node.
"""

from collections.abc import Callable, Mapping
from pathlib         import Path
from pytest          import Config, MonkeyPatch, fixture, mark, param
from subprocess      import run


@fixture(autouse=True)
def stand_ins(
    install_stand_ins : Callable[..., Path],
    monkeypatch       : MonkeyPatch,
    pytestconfig      : Config,
    tmp_path          : Path
):
    """
    Makes `tmp_path` the working directory and links each program a
    `site` task starts from `node_modules/.bin/` there, and `node`, to the
    stand-in.
    """
    programs = tmp_path / "node_modules/.bin"

    install_stand_ins("echo.sh", "node")

    monkeypatch.chdir(tmp_path)
    programs.mkdir(parents=True)

    for program in ("oxlint", "tsc", "vitest"):
        (programs / program).symlink_to(
            pytestconfig.rootpath / "tests/tasks/fixtures/echo.sh"
        )


def test_affected_asks_vitest_for_the_files_changed_since_main(
    printed: Callable[..., list[str]]
):
    """
    Pins that `site:affected` runs Vitest once over the files changed since
    the merge base with `origin/main`, forwarding `--reporter=dot` after
    the configuration.
    """
    assert printed("site/affected", "--reporter=dot") == [
        "run", "--changed", "origin/main",
        "--config", ".vitepress/config/vitest.ts", "--reporter=dot"
    ]


@mark.parametrize(
    ("shell", "output"),
    [
        param({}, "default", id="local"),
        param({"GITHUB_ACTIONS": "true"}, "github", id="actions")
    ],
    indirect = ["shell"]
)
def test_lint_asks_oxlint_for_annotations_under_github_actions(
    output  : str,
    printed : Callable[..., list[str]],
    shell   : dict[str, str]
):
    """
    Pins the argument list `site:lint` hands Oxlint, asking for annotations
    under GitHub Actions and for its default format elsewhere, and
    forwarding `--quiet` after its own flags and ahead of the folder Oxlint
    reads, before Node runs the line check from standard input.
    """
    assert printed("site/lint", "--quiet") == [
        "--config", ".vitepress/config/.oxlintrc.json", "--format", output,
        "--quiet", ".vitepress", "--input-type=module"
    ]


def test_lint_exits_1_when_the_line_check_fails_after_oxlint_passes(
    pytestconfig : Config,
    tmp_path     : Path
):
    """
    Asserts that `site:lint` exits 1 once the line check fails though Oxlint
    passes, Oxlint having read `.vitepress` first.
    """
    node = tmp_path / "stand-ins/node"

    node.unlink()
    node.symlink_to("/usr/bin/false")

    result = run(
        [pytestconfig.rootpath / ".mise/tasks/site/lint"],
        capture_output = True,
        text           = True
    )

    assert (result.returncode, result.stdout.splitlines()[-1]) == (1, ".vitepress")


def test_lint_names_the_file_and_line_of_a_line_past_110_characters(
    pytestconfig : Config,
    tmp_path     : Path
):
    """
    Asserts that `site:lint` runs the real line check from `docs/` once
    Oxlint passes, exiting 1 and naming the file and line of a line past
    110 characters.
    """
    lib    = tmp_path / "docs/.vitepress/lib"
    source = pytestconfig.rootpath / "docs/.vitepress/lib"
    stand  = tmp_path / "stand-ins/node"
    node   = run(
        ["mise", "which", "node"],
        capture_output = True,
        cwd            = pytestconfig.rootpath,
        text           = True
    )

    (tmp_path / ".git").mkdir()
    stand.unlink()
    stand.symlink_to(node.stdout.strip())

    for module in ("config/paths.ts", "proof/lines.ts"):
        (lib / module).parent.mkdir(exist_ok=True, parents=True)
        (lib / module).write_text((source / module).read_text())

    (tmp_path / "node_modules").rename(tmp_path / "docs/node_modules")

    (lib / "long.ts").write_text(f"// {'x' * 108}\n")

    result = run(
        [pytestconfig.rootpath / ".mise/tasks/site/lint"],
        capture_output = True,
        cwd            = tmp_path / "docs",
        text           = True
    )

    assert (result.returncode, result.stderr.split(" runs ")[0]) == (
        1, "docs/.vitepress/lib/long.ts:1"
    )


def test_lint_runs_the_line_check_after_oxlint_fails_and_exits_1(
    pytestconfig : Config,
    tmp_path     : Path
):
    """
    Asserts that `site:lint` still starts the line check once Oxlint exits
    1, and exits 1 itself though the check passes.
    """
    oxlint = tmp_path / "node_modules/.bin/oxlint"

    oxlint.unlink()
    oxlint.symlink_to("/usr/bin/false")

    result = run(
        [pytestconfig.rootpath / ".mise/tasks/site/lint"],
        capture_output = True,
        text           = True
    )

    assert (result.returncode, result.stdout) == (1, "--input-type=module\n")


@mark.usefixtures("clone")
def test_typecheck_hands_tsc_its_project_and_arguments(
    printed: Callable[..., list[str]]
):
    """
    Pins that `site:typecheck` starts `tsc` on the site's project in a
    checkout holding no single-file component, forwarding `--noEmit` after
    the project.
    """
    assert printed("site/typecheck", "--noEmit") == [
        "-p", ".vitepress/tsconfig.json", "--noEmit"
    ]


@mark.usefixtures("clone")
def test_typecheck_refuses_a_single_file_component_before_tsc_starts(
    checkout     : Callable[[Mapping[str, str]], None],
    pytestconfig : Config
):
    """
    Asserts that `site:typecheck` exits 1 on a checkout holding a `.vue`
    file git lists, naming the file, and starts no `tsc`.
    """
    checkout({"Card.vue": "<template />\n"})

    result = run(
        [pytestconfig.rootpath / ".mise/tasks/site/typecheck"],
        capture_output = True,
        text           = True
    )

    assert (result.returncode, result.stdout, result.stderr) == (
        1,
        "",
        "The site declares every component as a .tsx module, so Card.vue has no "
        "place\n"
    )
