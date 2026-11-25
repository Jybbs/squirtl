"""
Pins the checks `mise doctor project` runs from `[doctor.checks]` in
`.mise/config.toml`, meaning that each check's `run` command passes on the
state its `description` names and fails on each state its `hint` repairs,
that the `cartridge` hint followed as written passes its check on a fresh
clone, and that `git status` stays clean over a `.venv` folder and a `.venv`
link alike.

Each case runs a check's `run` command through `sh -o errexit -c`, the
inline shell mise runs a check in when the check declares no `shell`, from
a tree under `tmp_path` holding only the files the case lays out, with
only the stand-ins it installs on the path, so no case reads the worktree's
`data/` or `.venv` or reaches a real `cc` or `mise`.
"""

from collections.abc import Callable, Mapping
from pathlib         import Path
from pytest          import Config, MonkeyPatch, TempPathFactory, fixture, mark, param
from re              import search
from shlex           import quote
from shutil          import which
from subprocess      import check_output, run
from tomllib         import loads

type Tree = Mapping[str, str | None]

OTHER  = "interpreters/other"
PINNED = "interpreters/pinned"


@fixture
def checks(pytestconfig: Config) -> dict[str, dict[str, str]]:
    """
    Reads each table under `[doctor.checks]` in the worktree's
    `.mise/config.toml`, keyed by the check's name.
    """
    config = (pytestconfig.rootpath / ".mise/config.toml").read_text(encoding="utf-8")

    return loads(config)["doctor"]["checks"]


@fixture
def lay_out(tmp_path: Path) -> Callable[[Tree], None]:
    """
    Builds a writer of a tree under `tmp_path`, where each path ending in
    `/` is a folder, each path beside `None` an empty file, and each other
    path a link to the path beside it under `tmp_path`.
    """
    def write(tree: Tree):
        """
        Writes each entry of `tree` under `tmp_path`, making the folders its
        path names.
        """
        for name, target in tree.items():
            entry = tmp_path / name

            entry.parent.mkdir(exist_ok=True, parents=True)

            if name.endswith("/"):
                entry.mkdir()
            elif target is None:
                entry.touch()
            else:
                entry.symlink_to(tmp_path / target)

    return write


@fixture
def passes(
    checks      : dict[str, dict[str, str]],
    monkeypatch : MonkeyPatch,
    tmp_path    : Path
) -> Callable[[str], bool]:
    """
    Builds a runner of one check's `run` command from `tmp_path` under the
    `sh` the path held before a case narrowed it.

    Returns:
        A function taking the check's name, which returns whether the
        command exited 0.
    """
    shell = which("sh")

    monkeypatch.setenv("CALLS", str(tmp_path / "calls"))

    return lambda check: run(
        [shell, "-o", "errexit", "-c", checks[check]["run"]],
        capture_output = True,
        cwd            = tmp_path
    ).returncode == 0


STATES = [
    param(
        "cartridge",
        {"data/rom.gb": None},
        None,
        False,
        True,
        id = "cartridge-rom-in-data"
    ),
    param(
        "cartridge",
        {"data/rom.gb": "rom/PokemonBlue.gb", "rom/PokemonBlue.gb": None},
        None,
        False,
        True,
        id = "cartridge-rom-linked-into-data"
    ),
    param("cartridge", {}, None, False, False, id="cartridge-fresh-clone"),
    param(
        "cartridge",
        {"data/other.gb": None},
        None,
        False,
        False,
        id = "cartridge-data-without-rom"
    ),
    param(
        "cartridge",
        {"data/rom.gb": "rom/PokemonBlue.gb"},
        None,
        False,
        False,
        id = "cartridge-dangling-link"
    ),
    param(
        "cartridge",
        {"data/rom.gb/": None},
        None,
        False,
        False,
        id = "cartridge-folder-at-rom"
    ),
    param("compiler", {}, "cc", False, True, id="compiler-runs"),
    param("compiler", {}, None, False, False, id="compiler-missing"),
    param("compiler", {}, "cc", True, False, id="compiler-failing"),
    param("lockfile", {}, "mise", False, True, id="lockfile-current"),
    param("lockfile", {}, "mise", True, False, id="lockfile-drifted"),
    param("venv", {}, "mise", False, True, id="venv-absent"),
    param(
        "venv",
        {".venv/bin/python": PINNED, PINNED: None},
        "mise",
        False,
        True,
        id = "venv-folder-on-the-pin"
    ),
    param(
        "venv",
        {".venv": "env", "env/bin/python": PINNED, PINNED: None},
        "mise",
        False,
        True,
        id = "venv-link-on-the-pin"
    ),
    param(
        "venv",
        {".venv/bin/python": PINNED, PINNED: None},
        "mise",
        True,
        False,
        id = "venv-pin-not-installed"
    ),
    param(
        "venv",
        {".venv/bin/python": OTHER, OTHER: None, PINNED: None},
        "mise",
        False,
        False,
        id = "venv-folder-on-another-interpreter"
    ),
    param(
        "venv",
        {
            ".venv"          : "env",
            "env/bin/python" : OTHER,
            OTHER            : None,
            PINNED           : None
        },
        "mise",
        False,
        False,
        id = "venv-link-on-another-interpreter"
    ),
    param(
        "venv",
        {".venv/": None, PINNED: None},
        "mise",
        False,
        False,
        id = "venv-folder-without-python"
    ),
    param("venv", {".venv": None, PINNED: None}, "mise", False, False, id="venv-file"),
    param(
        "venv",
        {".venv": "env", PINNED: None},
        "mise",
        False,
        False,
        id = "venv-dangling-link"
    )
]


def test_every_declared_check_has_states(checks: dict[str, dict[str, str]]):
    """
    Pins that the rows of `STATES` cover each check `.mise/config.toml`
    declares, so a check added there fails this case until its states land.
    """
    assert {state.values[0] for state in STATES} == set(checks)


@mark.parametrize(("check", "tree", "program", "failing", "passing"), STATES)
def test_each_check_passes_only_on_the_state_its_description_names(
    check             : str,
    failing           : bool,
    install_stand_ins : Callable[..., Path],
    lay_out           : Callable[[Tree], None],
    monkeypatch       : MonkeyPatch,
    passes            : Callable[[str], bool],
    passing           : bool,
    program           : str | None,
    tmp_path          : Path,
    tree              : Tree
):
    """
    Pins that each check passes on the state its `description` names and
    fails on each state its `hint` repairs, with only the stand-in the row
    names on the path, every call to it exiting 1 where `failing` holds, and
    the stand-in `mise` answering `mise which python` with the interpreter
    at `interpreters/pinned`.
    """
    stand_ins = install_stand_ins("stand-in.sh", *filter(None, [program]))

    monkeypatch.setenv("PATH", str(stand_ins))
    monkeypatch.setenv("ANSWER", str(tmp_path / PINNED))
    monkeypatch.setenv("FAILING", "*" if failing else "")
    lay_out(tree)

    assert passes(check) is passing


def test_the_cartridge_hint_followed_as_written_passes_on_a_fresh_clone(
    checks           : dict[str, dict[str, str]],
    passes           : Callable[[str], bool],
    tmp_path         : Path,
    tmp_path_factory : TempPathFactory
):
    """
    Pins that the command the `cartridge` hint gives, run from a clone
    holding no `data/` folder with `<rom>` naming a ROM outside it, leaves
    the check passing.
    """
    rom     = tmp_path_factory.mktemp("rom") / "PokemonBlue.gb"
    command = search(r"`([^`]*<rom>[^`]*)`", checks["cartridge"]["hint"])[1]

    rom.touch()
    run(
        ["sh", "-c", command.replace("<rom>", quote(str(rom)))],
        check = True,
        cwd   = tmp_path
    )

    assert passes("cartridge")


@mark.parametrize("linked", [param(False, id="folder"), param(True, id="link")])
def test_git_status_stays_clean_over_each_venv(
    checkout         : Callable[[Mapping[str, str]], None],
    git              : Callable[..., None],
    linked           : bool,
    pytestconfig     : Config,
    tmp_path         : Path,
    tmp_path_factory : TempPathFactory
):
    """
    Pins that the worktree's `.gitignore` keeps `.venv` out of `git
    status` in a clone holding it, whether `.venv` is a folder holding an
    environment or a link to one outside the clone.
    """
    checkout(
        {
            ".gitignore": (pytestconfig.rootpath / ".gitignore").read_text(
                encoding = "utf-8"
            )
        }
    )

    for command in (["init"], ["add", "."], ["commit", "--message", "Ignore"]):
        git(*command)

    environment = tmp_path_factory.mktemp("env") if linked else tmp_path / ".venv"

    (environment / "bin").mkdir(parents=True)
    (environment / "bin/python").touch()

    if linked:
        (tmp_path / ".venv").symlink_to(environment)

    assert check_output(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        text = True
    ) == ""
