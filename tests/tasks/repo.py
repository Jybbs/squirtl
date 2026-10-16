"""
Pins what the `repo` tasks that write to GitHub send for the registries the
checkout ships, meaning the commands `repo:labels` and `repo:rulesets` print
and send once the reader confirms them, and the live labels `repo:labels`
lists for adding to the registry or deleting by hand.

Each case runs its task script in-process from the worktree root, where
the script reads the shipped files, and the `fp` fixture pytest-subprocess
provides answers every `gh` command, so no case reaches GitHub.
"""

from collections.abc   import Callable
from json              import dumps
from pytest            import CaptureFixture, Config, MonkeyPatch, fixture, mark, param, raises
from pytest_subprocess import FakeProcess
from runpy             import run_path
from shlex             import split
from syrupy.assertion  import SnapshotAssertion

from squirtl.repo.schemas import Labels


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
