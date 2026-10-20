"""
Pins what the `repo` tasks decide from their inputs, covering:

- The commands `repo:labels` and `repo:rulesets` print for the registries
  the checkout ships, and send once the reader confirms them
- The live labels `repo:labels` lists for adding to the registry or
  deleting by hand
- The part of the version `repo:bump` moves, and the version it writes
  into `CITATION.cff`

Each registry case runs its task script in-process from the worktree
root, where the script reads the shipped files, and the `fp` fixture
pytest-subprocess provides answers every `gh` command, so no case reaches
GitHub. Each `repo:bump` case runs the task through the real `mise` from a
placeholder checkout under `tmp_path`, where the stand-in under `fixtures/`
answers for `uv`.
"""

from collections.abc   import Callable
from json              import dumps
from pathlib           import Path
from pytest            import CaptureFixture, Config, MonkeyPatch, fixture, mark, param, raises
from pytest_subprocess import FakeProcess
from runpy             import run_path
from shlex             import split
from subprocess        import CompletedProcess, run
from syrupy.assertion  import SnapshotAssertion

from squirtl.repo.schemas import Labels


@fixture
def bump(
    checkout          : Callable[..., None],
    confine_mise      : Callable[[Path, Path], None],
    install_stand_ins : Callable[..., Path],
    monkeypatch       : MonkeyPatch,
    pytestconfig      : Config,
    tmp_path          : Path
) -> Callable[..., CompletedProcess[str]]:
    """
    Lays out `tmp_path` as a checkout holding an empty `.mise/config.toml`,
    a link to the worktree's `repo:bump` task, and a placeholder
    `CITATION.cff`, and builds a runner of that task through the real `mise`
    from there, which `confine_mise` confines to that checkout.

    The stand-in answers for `uv`, writing each call it receives to the file
    `CALLS` names, printing `ANSWER` where a case sets it, and exiting 1
    where its call matches the shell pattern `FAILING` holds.

    Returns:
        A function taking the arguments to start the task with.
    """
    checkout(
        {
            ".mise/config.toml" : "",
            "CITATION.cff"      : "cff-version     : 1.2.0\nversion         : 0.1.0\n"
        }
    )
    (tmp_path / ".mise/tasks/repo").mkdir(parents=True)
    (tmp_path / ".mise/tasks/repo/bump").symlink_to(
        pytestconfig.rootpath / ".mise/tasks/repo/bump"
    )

    confine_mise(tmp_path, install_stand_ins("stand-in.sh", "uv"))
    monkeypatch.setenv("CALLS", str(tmp_path / "calls"))

    return lambda *arguments: run(
        ["mise", "run", "repo:bump", *arguments],
        capture_output = True,
        text           = True
    )


@fixture
def task(monkeypatch: MonkeyPatch, pytestconfig: Config) -> Callable[[str], int]:
    """
    Builds a runner of the task script `.mise/tasks/repo/<name>.py` from the
    worktree root, which returns the status the script exits with.
    """
    monkeypatch.chdir(pytestconfig.rootpath)

    def start(name: str) -> int:
        """
        Runs the script as its `__main__` block would.
        """
        with raises(SystemExit) as exited:
            run_path(f".mise/tasks/repo/{name}.py", run_name="__main__")

        return exited.value.code

    return start


@mark.parametrize(
    ("name", "listing", "live"),
    [
        param("labels", ["gh", "label", "list", FakeProcess.any()], [], id="labels"),
        param(
            "rulesets",
            [
                "gh", "api", "repos/{owner}/{repo}/rulesets?includes_parents=false",
                FakeProcess.any()
            ],
            [[
                {"id": 7, "name": "main branch protection"},
                {"id": 9, "name": "release tag protection"}
            ]],
            id = "rulesets"
        )
    ]
)
def test_each_task_sends_the_commands_its_snapshot_holds(
    answered : Callable[[str], None],
    capsys   : CaptureFixture[str],
    fp       : FakeProcess,
    listing  : list[str | FakeProcess.any],
    live     : list[list[dict[str, int | str]]],
    name     : str,
    snapshot : SnapshotAssertion,
    task     : Callable[[str], int]
):
    """
    Pins every command each task prints for the shipped registries, where
    GitHub carries no label and carries both rulesets under the names
    their files declare, and that each command a task sends once the reader
    answers `y` is the one it printed.
    """
    fp.register(listing, stdout=dumps(live))
    answered("y\n")
    fp.register(["gh", fp.any()])
    fp.keep_last_process(True)

    assert task(name) == 0
    assert (printed := capsys.readouterr().out) == snapshot
    assert list(fp.calls)[2:] == [
        split(line.partition(" <<< ")[0])
        for line in printed.splitlines()
        if line.startswith("gh ")
    ]


def test_labels_lists_each_live_label_the_registry_leaves_out(
    capsys : CaptureFixture[str],
    fp     : FakeProcess,
    task   : Callable[[str], int]
):
    """
    Pins that `repo:labels` lists a label GitHub carries that the shipped
    registry leaves out, for adding to the registry or deleting by hand, and
    sends nothing and asks nothing where GitHub carries every shipped label
    as the registry declares it.
    """
    fp.register(
        ["gh", "label", "list", fp.any()],
        stdout = dumps(
            [
                *(label.model_dump() for label in Labels.read().labels),
                {"color": "ffffff", "description": "", "name": "wontfix"}
            ]
        )
    )

    assert task("labels") == 0
    assert capsys.readouterr().out == (
        "Left as they are, since no file under .github/ declares them:\n"
        "  the label wontfix\n"
        "GitHub already matches the files under .github/\n"
    )
    assert len(fp.calls) == 1


@mark.parametrize(
    ("arguments", "part", "version"),
    [
        param([], "minor", "0.2.0", id="minor-by-default"),
        param(["patch"], "patch", "0.1.1", id="patch")
    ]
)
def test_bump_moves_the_part_its_argument_names(
    arguments   : list[str],
    bump        : Callable[..., CompletedProcess[str]],
    monkeypatch : MonkeyPatch,
    part        : str,
    tmp_path    : Path,
    version     : str
):
    """
    Pins that `repo:bump` hands `uv version` the minor part where it is
    given no argument and the patch part where it is given `patch`, unlocked
    and unsynced so uv rewrites `uv.lock` and leaves `.venv` alone. The
    task then writes the version uv prints onto the `version` line of
    `CITATION.cff`, keeping that line's alignment and leaving `cff-version`
    as it was.
    """
    monkeypatch.setenv("ANSWER", version)

    assert bump(*arguments).returncode == 0
    assert (tmp_path / "calls").read_text(encoding="utf-8") == (
        f"uv version --bump {part} --no-locked --no-sync --short\n"
    )
    assert (tmp_path / "CITATION.cff").read_text(encoding="utf-8") == (
        f"cff-version     : 1.2.0\nversion         : {version}\n"
    )


@mark.parametrize(
    ("arguments", "shell", "reached"),
    [
        param(["major"], {}, False, id="major"),
        param([], {"FAILING": "uv version*"}, True, id="uv-fails")
    ],
    indirect = ["shell"]
)
def test_a_refused_bump_leaves_the_citation_as_it_was(
    arguments : list[str],
    bump      : Callable[..., CompletedProcess[str]],
    reached   : bool,
    shell     : dict[str, str],
    tmp_path  : Path
):
    """
    Pins that `repo:bump` exits nonzero and leaves `CITATION.cff` as it was
    where mise refuses a part other than `minor` or `patch` before calling
    uv, and where `uv version` fails.
    """
    citation = (tmp_path / "CITATION.cff").read_text(encoding="utf-8")

    assert bump(*arguments).returncode != 0
    assert (tmp_path / "calls").exists() is reached
    assert (tmp_path / "CITATION.cff").read_text(encoding="utf-8") == citation
