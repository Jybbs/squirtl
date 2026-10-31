"""
Pins what the `site` tasks decide from the shell and the checkout they run
in, meaning the output format `site:lint` chooses for the shell it runs in,
each further argument `site:lint` and `site:typecheck` forward after their
own flags, and the single-file component `site:typecheck` refuses before
`tsc` starts.

Each case runs its task from `tmp_path`, where the links under
`node_modules/.bin/` lead to the stand-in under `fixtures/`, which prints
each argument it receives on a line of its own, so no case starts Oxlint
or `tsc`.
"""

from collections.abc import Callable, Mapping
from pathlib         import Path
from pytest          import Config, MonkeyPatch, fixture, mark, param
from subprocess      import run


@fixture(autouse=True)
def stand_ins(monkeypatch: MonkeyPatch, pytestconfig: Config, tmp_path: Path):
    """
    Makes `tmp_path` the working directory and links each program a `site`
    task starts from `node_modules/.bin/` there to the stand-in.
    """
    programs = tmp_path / "node_modules/.bin"

    monkeypatch.chdir(tmp_path)
    programs.mkdir(parents=True)

    for program in ("oxlint", "tsc"):
        (programs / program).symlink_to(
            pytestconfig.rootpath / "tests/tasks/fixtures/echo.sh"
        )


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
    reads.
    """
    assert printed("site/lint", "--quiet") == [
        "--config", ".vitepress/.oxlintrc.json", "--format",
        output, "--quiet", ".vitepress"
    ]


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
