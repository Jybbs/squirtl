"""
Pins what `repo:lift` reads from each tool's report and writes into a
checkout, covering:

- The open alerts Dependabot lists and the lift clearing each
- The line `Checkout` writes a version on and what refuses the write
- What a scratch clone holds and the variables its commands run under
- The lifts crossing a major version, and the table every lift prints in
- The lift each manager names from its tool's report and what it writes
- What an attempt leaves behind, the verdict a trial reaches, and the status
  each route through `Lifts.lift` exits with

Each case writes the files it reads under `tmp_path` through the `checkout`
fixture, and the `fp` fixture pytest-subprocess provides answers every
command but the `git` a scratch clone runs, so no case reaches a registry
or GitHub.
"""

from collections.abc   import Callable, Mapping
from datetime          import UTC, datetime, timedelta
from io                import StringIO
from json              import dumps
from os                import pathsep
from packaging.version import Version
from pathlib           import Path
from pytest            import (
    CaptureFixture, Config, MonkeyPatch, fixture, mark, param, raises
)
from pytest_subprocess import FakeProcess
from subprocess        import CalledProcessError
from syrupy.assertion  import SnapshotAssertion
from sysconfig         import get_path
from textwrap          import dedent
from typing            import ClassVar, Self

from squirtl.repo.lifts import (
    ActionLift, ActionLifts, Alert, Attempt, Checkout, Holds, Lift, Lifts, Manager, PackageLifts,
    Pylock, PylockPackage, RequirementLifts, SiteLifts, ToolLifts, Trial,
    concurrently, table_text, version_of
)

ALERTS = [
    "gh", "api", "repos/{owner}/{repo}/dependabot/alerts", "--method",
    "GET", "--paginate", "--slurp", "-f",
    "per_page=100", "-f", "state=open"
]
COMPILE = [
    "uv", "pip", "compile", "--format",
    "pylock.toml", "--no-header", "--quiet", "--universal"
]
PINNED  = "a" * 40
TARGET  = "b" * 40
RELEASE = dumps({"publishedAt": "2026-10-01T00:00:00Z", "tagName": "v5.0.0"})
QUIET   = {
    ".mise/tasks/repo/bare.py"  : dedent(
        """\
        #!/usr/bin/env -S uv run --exact --locked
        # /// script
        # dependencies = []
        # ///
        """
    ),
    ".mise/tasks/repo/plain.py" : "#!/usr/bin/env python3\n"
}
SCRIPT = dedent(
    """\
    #!/usr/bin/env -S uv run --exact --locked
    # /// script
    # dependencies = ["pyyaml==6.0.2"]
    # requires-python = ">=3.14"
    # ///
    """
)
SITE = dumps(
    {
        "devDependencies": {
            "@types/node" : "26.6.5",
            "knip"        : "5.60.0",
            "oxlint"      : "1.0.0",
            "vitepress"   : "2.0.0-alpha.20"
        }
    }
)
WORKFLOW = dedent(
    f"""\
    name: Pages
    on: push
    jobs:
      deploy:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@{PINNED}
          - uses: cloudflare/wrangler-action@{PINNED}
            with:
              wranglerVersion : 4.151.3
    """
)


class Reporting(Manager):
    """
    A manager whose report names one lift, which it writes into `lifted.txt`
    at the root of the checkout, one name per line.
    """

    ecosystem: ClassVar[str | None] = "pip"

    @classmethod
    def read(cls) -> Self:
        """
        Reports the lift of `setuptools` past the release an alert names.
        """
        return cls(lifts=(lift_of("setuptools 84.0.0 84.2.1"),))

    def write(self, checkout: Checkout):
        """
        Writes the name of each lift, raising `ValueError` where a lift is
        named `broken`.
        """
        names = [lift.name for lift in self.lifts]

        if "broken" in names:
            raise ValueError("`uv.lock` matches nothing")

        (checkout.root / "lifted.txt").write_text("\n".join(names), encoding="utf-8")


@fixture
def tagged(fp: FakeProcess) -> Callable[[str, str], None]:
    """
    Builds a function that registers the reply `gh release view` gives for a
    repository's latest release beside the lines `git ls-remote` prints for
    its tags, for `actions/checkout` where the call names no other.
    """
    def register(lines: str, repository: str = "actions/checkout"):
        """
        Registers the two commands reading `repository`.
        """
        fp.register(
            [
                "gh", "release", "view", "--json",
                "publishedAt,tagName", "--repo", repository
            ],
            stdout = RELEASE
        )
        fp.register(
            ["git", "ls-remote", "--tags", f"https://github.com/{repository}"],
            stdout = lines
        )

    return register


@fixture
def refused(monkeypatch: MonkeyPatch):
    """
    Fails a case where the lift goes on to a trial or a write.
    """
    def refuse(*_: object):
        """
        Raises where the case reaches either step.
        """
        raise AssertionError("The lift reached a trial or a write")

    monkeypatch.setattr(Lifts, "tried", refuse)
    monkeypatch.setattr(Lifts, "write", refuse)


def alert_of(
    ecosystem : str        = "pip",
    package   : str        = "setuptools",
    patched   : str | None = "84.1.0"
) -> dict[str, object]:
    """
    Builds an alert as Dependabot's endpoint reports it, nesting each field
    the record reads among fields it leaves out.
    """
    return {
        "number" : 3,
        "state"  : "open",

        "dependency": {
            "manifest_path" : "uv.lock",
            "package"       : {"ecosystem": ecosystem, "name": package}
        },

        "security_advisory": {"ghsa_id": "GHSA-xmj3-9gf7-h52w"},

        "security_vulnerability": {
            "first_patched_version"    : {"identifier": patched} if patched else None,
            "vulnerable_version_range" : ">= 38.2.2, < 84.1.0"
        }
    }


def lift_of(pin: str, **fields: object) -> Lift:
    """
    Builds the lift `pin` spells as its name, its current version, and its
    newest version, under `uv.lock` where `fields` names no other home.
    """
    name, current, newest = pin.split()

    return Lift(
        **{"home": Path("uv.lock")} | fields,
        current = current,
        name    = name,
        newest  = newest
    )


def lifts_of(*lifts: Lift, **fields: object) -> Lifts:
    """
    Gathers `lifts` under one manager.
    """
    return Lifts(found=(Reporting(lifts=lifts),), **fields)


def pylock_of(*packages: tuple[str, str]) -> str:
    """
    Writes the lockfile `uv pip compile` prints for each name and version in
    `packages`, each release's one wheel uploaded on the first of October.
    """
    return "".join(
        f'[[packages]]\nname = "{name}"\nversion = "{version}"\n'
        f"wheels = [{{ upload-time = 2026-10-01T00:00:00Z }}]\n"
        for name, version in packages
    )


def test_a_checkout_raises_where_a_command_it_must_run_fails(
    fp       : FakeProcess,
    tmp_path : Path
):
    """
    Pins that `run` turns a nonzero exit into `CalledProcessError` holding
    the command's own status, the failure an attempt reports as failing.
    """
    fp.register(["mise", "lock"], returncode=3)

    with raises(CalledProcessError) as caught:
        Checkout(root=tmp_path).run("mise", "lock")

    assert caught.value.returncode == 3


@mark.parametrize(
    ("text", "version"),
    [
        param("1.2.3", Version("1.2.3"), id="plain"),
        param("v4.2.2", Version("4.2.2"), id="leading-v"),
        param("2.0.0-alpha.21", Version("2.0.0a21"), id="npm-prerelease"),
        param("latest", None, id="tag-naming-no-version"),
        param(PINNED, None, id="commit")
    ]
)
def test_version_of_parses_a_version_and_returns_none_for_anything_else(
    text    : str,
    version : Version | None
):
    """
    Pins which texts name a version, the rest being the tags and commits a
    pin can hold instead.
    """
    assert version_of(text) == version


def test_a_clean_clone_applies_no_change(clone: Path):
    """
    Pins that a checkout with nothing uncommitted clones as it was
    committed, `git apply` refusing an empty patch were it to run.
    """
    copied = Checkout(root=clone).cloned(clone / "data/scratch", StringIO()).root

    assert (copied / "uv.lock").read_text(encoding="utf-8") == "version = 1\n"


@mark.parametrize(
    ("alert", "ecosystem", "lift", "clears"),
    [
        param(
            alert_of(),
            "pip",
            lift_of("setuptools 84.0.0 84.1.0"),
            True,
            id = "newest-at-the-first-patched-release"
        ),
        param(
            alert_of(),
            "pip",
            lift_of("setuptools 84.0.0 84.2.1"),
            True,
            id = "newest-past-the-first-patched-release"
        ),
        param(
            alert_of(),
            "pip",
            lift_of("setuptools 83.0.0 84.0.9"),
            False,
            id = "newest-below-the-first-patched-release"
        ),
        param(
            alert_of(),
            "pip",
            lift_of("setuptools 84.1.0 84.2.1"),
            False,
            id = "current-already-at-the-first-patched-release"
        ),
        param(
            alert_of(package="PyYAML", patched="6.0.3"),
            "pip",
            lift_of("pyyaml 6.0.2 6.0.3"),
            True,
            id = "names-compared-as-pep-503-normalizes-them"
        ),
        param(
            alert_of(),
            "pip",
            lift_of("hatchling 84.0.0 84.2.1"),
            False,
            id = "another-package"
        ),
        param(
            alert_of(),
            "npm",
            lift_of("setuptools 84.0.0 84.2.1"),
            False,
            id = "another-ecosystem"
        ),
        param(
            alert_of(),
            None,
            lift_of("setuptools 84.0.0 84.2.1"),
            False,
            id = "a-tool-whose-pins-no-alert-names"
        ),
        param(
            alert_of(patched=None),
            "pip",
            lift_of("setuptools 84.0.0 84.2.1"),
            False,
            id = "no-patched-release-published"
        ),
        param(
            alert_of(),
            "pip",
            lift_of(f"setuptools {PINNED} 84.2.1"),
            False,
            id = "a-commit-names-no-version"
        )
    ]
)
def test_an_alert_is_cleared_by_a_lift_crossing_its_first_patched_release(
    alert     : dict[str, object],
    clears    : bool,
    ecosystem : str | None,
    lift      : Lift
):
    """
    Pins that a lift clears an alert only where it moves the package the
    alert names, in the alert's ecosystem, from below the first release past
    the vulnerability to that release or later.
    """
    assert Alert.model_validate(alert).clears(ecosystem, lift) is clears


@mark.parametrize(
    ("text", "key", "current", "prefix", "written"),
    [
        param(
            'min_version = "2026.9.18"\n',
            "min_version",
            "2026.9.18",
            "",
            'min_version = "9.9.9"\n',
            id = "toml"
        ),
        param(
            'node   = "26.12.1"\nuv     = "0.12.13"\n',
            "uv",
            "0.12.13",
            "",
            'node   = "26.12.1"\nuv     = "9.9.9"\n',
            id = "toml-aligned"
        ),
        param(
            'required-version = "==0.12.13"\n',
            "required-version",
            "0.12.13",
            "==",
            'required-version = "==9.9.9"\n',
            id = "toml-behind-a-prefix"
        ),
        param(
            "        wranglerVersion : 4.151.3\n",
            "wranglerVersion",
            "4.151.3",
            "",
            "        wranglerVersion : 9.9.9\n",
            id = "yaml-unquoted"
        ),
        param(
            '# requires-python = ">=3.14"\n',
            "requires-python",
            "3.14",
            ">=",
            '# requires-python = ">=9.9.9"\n',
            id = "inline-metadata"
        )
    ]
)
def test_a_checkout_writes_a_version_on_the_line_assigning_its_key(
    checkout : Callable[[Mapping[str, str]], None],
    current  : str,
    key      : str,
    prefix   : str,
    text     : str,
    tmp_path : Path,
    written  : str
):
    """
    Pins that the pattern `assigned` builds finds the version in each form
    a home writes it in, and that `respell` leaves the rest of the file as
    it stands.
    """
    checkout({"file": text})

    Checkout(root=tmp_path).respell(
        Path("file"),
        Checkout.assigned(current, key, prefix),
        "9.9.9"
    )

    assert (tmp_path / "file").read_text(encoding="utf-8") == written


@mark.parametrize(
    ("text", "times"),
    [
        param('uv = "0.11.0"\n', 0, id="no-match"),
        param('uv = "0.12.13"\n[other]\nuv = "0.12.13"\n', 2, id="two-matches")
    ]
)
def test_a_checkout_refuses_a_write_matching_other_than_once(
    checkout : Callable[[Mapping[str, str]], None],
    text     : str,
    times    : int,
    tmp_path : Path
):
    """
    Pins that a home matching the pattern zero times or twice raises before
    the file changes, so a write never lands in a line it did not identify.
    """
    checkout({"file": text})

    with raises(ValueError, match=f"{times} times rather than once"):
        Checkout(root=tmp_path).respell(
            Path("file"),
            Checkout.assigned("0.12.13", "uv"),
            "9.9.9"
        )

    assert (tmp_path / "file").read_text(encoding="utf-8") == text


def test_a_clone_holds_the_tree_as_it_stands_without_any_ignored_file(
    checkout : Callable[[Mapping[str, str]], None],
    clone    : Path
):
    """
    Pins that a scratch clone carries a modified tracked file, an untracked
    file in a new folder, and an untracked link kept as a link, and leaves
    out a file `.gitignore` excludes, with the checkout left as it stood.
    """
    checkout(
        {
            "data/ignored.txt"  : "ignored\n",
            "new/untracked.txt" : "untracked\n",
            "uv.lock"           : "version = 2\n"
        }
    )
    (clone / "link").symlink_to("uv.lock")

    copied = Checkout(root=clone).cloned(clone / "data/scratch", StringIO()).root

    assert (copied / "uv.lock").read_text(encoding="utf-8") == "version = 2\n"
    assert (copied / "new/untracked.txt").read_text(encoding="utf-8") == "untracked\n"
    assert (copied / "link").readlink() == Path("uv.lock")
    assert not (copied / "data").exists()


def test_a_clone_runs_its_commands_free_of_the_calling_uv_run(
    clone       : Path,
    monkeypatch : MonkeyPatch
):
    """
    Pins that each variable the calling `uv run` sets, and the folder of its
    environment's scripts, stay out of the clone's commands, whereas mise
    trusts the clone and the rest of the task's variables pass through.
    """
    for name in Checkout.uv_run:
        monkeypatch.setenv(name, "set")

    monkeypatch.setenv("KEPT", "kept")
    monkeypatch.setenv("PATH", get_path("scripts"), prepend=pathsep)

    destination = clone / "data/scratch"
    environment = Checkout(root=clone).cloned(destination, StringIO()).env

    assert Checkout.uv_run.isdisjoint(environment)
    assert get_path("scripts") not in environment["PATH"].split(pathsep)
    assert environment["KEPT"] == "kept"
    assert environment["MISE_TRUSTED_CONFIG_PATHS"] == str(destination)


def test_a_compile_resolves_its_requirements_through_standard_input(fp: FakeProcess):
    """
    Pins the flags and the requirements `uv pip compile` receives, and that
    the lockfile keys each package by the name PEP 503 normalizes.
    """
    received = []

    fp.register(
        [*COMPILE, "--no-deps", "-"],
        stdin_callable = received.append,
        stdout         = pylock_of(("PyYAML", "6.0.3"))
    )

    named = Pylock.compiled(["PyYAML==6.0.3", "torch"], "--no-deps").named

    assert received == ["PyYAML==6.0.3\ntorch"]
    assert named["pyyaml"].version == Version("6.0.3")


def test_a_held_pin_stays_out_of_the_trial_and_the_write_while_the_table_lists_it(
    capsys      : CaptureFixture[str],
    monkeypatch : MonkeyPatch
):
    """
    Pins that the table still lists a held pin beside the line saying why it
    stays, whether the tracked file or `--hold` names it, and that the write
    takes every other lift alone.
    """
    written = []

    monkeypatch.setattr(
        Lifts,
        "write",
        lambda self, checkout: written.extend(lift.name for lift in self.lifts)
    )

    lifts = lifts_of(
        lift_of("a 1.0.0 2.0.0"),
        lift_of("b 1.0.0 2.0.0"),
        lift_of("c 1.0.0 2.0.0"),
        holds = {"a": "the reason"}
    )

    assert lifts.lift(held=("b",), trying=False, writing=True) == 0

    printed = capsys.readouterr().out.splitlines()

    assert written == ["c"]
    assert [line.split()[0] for line in printed[2:-2]] == ["a", "b", "c"]
    assert printed[-2:] == [
        "Leaving a at 1.0.0, because the reason",
        "Leaving b at 1.0.0, because `--hold` names it for this run"
    ]


def test_a_hold_names_each_row_of_its_pin_at_the_version_that_row_holds(
    capsys: CaptureFixture[str]
):
    """
    Pins that a pin the table lists twice, in two files holding two
    versions, prints one line per row, and that the tracked reason stands
    where `--hold` names the pin too.
    """
    lifts = lifts_of(
        lift_of("a 1.0.0 2.0.0"),
        lift_of("a 1.5.0 2.0.0", home=Path("pyproject.toml")),
        holds = {"a": "the reason"}
    )

    assert lifts.lift(held=("a",), trying=False, writing=False) == 0
    assert capsys.readouterr().out.splitlines()[-2:] == [
        "Leaving a at 1.0.0, because the reason",
        "Leaving a at 1.5.0, because the reason"
    ]


def test_a_lock_with_nothing_to_update_compiles_nothing(fp: FakeProcess):
    """
    Pins that no `Update` line reads as no lift, with no `uv pip compile`,
    which `fp` refuses since no case registers it.
    """
    fp.register(
        ["uv", "lock", "--color", "never", "--dry-run", "--no-locked", "--upgrade"],
        stderr = "Resolved 143 packages in 12ms\n"
    )

    assert PackageLifts.read().lifts == ()


def test_a_lock_write_upgrades_each_lifted_package_alone(
    fp       : FakeProcess,
    tmp_path : Path
):
    """
    Pins that the write names each lift through `--upgrade-package`, so a
    package a hold leaves out stays where it stands.
    """
    fp.register(
        [
            "uv", "lock", "--no-locked", "--upgrade-package",
            "setuptools", "--upgrade-package", "torch"
        ]
    )

    PackageLifts(
        lifts = (
            lift_of("setuptools 84.0.0 84.2.1"),
            lift_of("torch 2.14.1 2.15.0")
        )
    ).write(Checkout(root=tmp_path))

    assert fp.call_count(["uv", "lock", fp.any()]) == 1


@mark.parametrize(
    ("name", "current", "newest", "major"),
    [
        param("uv", "1.2.3", "1.2.4", False, id="patch"),
        param("uv", "1.2.3", "1.3.0", False, id="minor-past-a-non-zero-major"),
        param("uv", "1.2.3", "2.0.0", True, id="major"),
        param("uv", "0.12.13", "0.12.14", False, id="patch-below-1"),
        param("uv", "0.12.13", "0.13.0", True, id="minor-below-1"),
        param("uv", "0.0.4", "0.0.5", True, id="patch-below-0.1"),
        param("uv", "0.0.0", "0.0.1", True, id="patch-of-an-all-zero-version"),
        param("mise", "2026.9.18", "2026.10.25", False, id="calendar-within-its-year"),
        param("mise", "2026.9.18", "2027.1.0", True, id="calendar-past-its-year"),
        param("python", "3.14.6", "3.14.10", False, id="python-patch"),
        param("python", "3.14.6", "3.15.1", True, id="python-minor"),
        param("node", "3.14.6", "3.15.1", False, id="minor-of-anything-but-python"),
        param("vitepress", "2.0.0-alpha.20", "2.0.0-alpha.21", False, id="prerelease"),
        param("actions/checkout", PINNED, "v5.0.0", False, id="commit-no-tag-names")
    ]
)
def test_a_lift_is_major_where_the_left_most_non_zero_part_changes(
    current : str,
    major   : bool,
    name    : str,
    newest  : str
):
    """
    Pins what crosses a major version for each kind of version a pin holds,
    the minor standing in for the `python` pin.
    """
    assert lift_of(f"{name} {current} {newest}").major is major


@mark.parametrize(
    ("released", "age"),
    [
        param(timedelta(days=3, hours=1), 3, id="whole-days-rounded-down"),
        param(timedelta(hours=1), 0, id="under-a-day"),
        param(None, None, id="the-manager-names-no-time")
    ]
)
def test_a_lift_counts_the_whole_days_since_its_newest_release(
    age      : int | None,
    released : timedelta | None
):
    """
    Pins the age a row prints, empty where the manager names no release
    time.
    """
    lift = lift_of("uv 1.0.0 1.0.1", released=released and datetime.now(UTC) - released)

    assert lift.age == age


def test_a_lock_write_with_no_lift_runs_nothing(fp: FakeProcess, tmp_path: Path):
    """
    Pins that an empty manager starts no `uv lock`, which would upgrade
    nothing and could still rewrite the lockfile.
    """
    PackageLifts(lifts=()).write(Checkout(root=tmp_path))

    assert not list(fp.calls)


def test_a_manager_names_every_alert_each_lift_clears():
    """
    Pins that `clearing` marks a lift with the advisories it clears, in the
    manager's own ecosystem, and leaves any other lift naming none.
    """
    cleared = Reporting(
        lifts = (
            lift_of("setuptools 84.0.0 84.2.1"),
            lift_of("hatchling 1.0.0 1.1.0")
        )
    ).clearing([Alert.model_validate(alert_of())])

    assert [lift.clears for lift in cleared.lifts] == [("GHSA-xmj3-9gf7-h52w",), ()]


@mark.parametrize(
    ("files", "released"),
    [
        param(
            {
                "sdist"  : {"upload-time": "2026-10-02T00:00:00Z"},
                "wheels" : [{"upload-time": "2026-10-01T00:00:00Z"}]
            },
            datetime(2026, 10, 1, tzinfo=UTC),
            id = "the-first-upload-across-its-files"
        ),
        param(
            {"sdist": {"upload-time": "2026-10-02T00:00:00Z"}},
            datetime(2026, 10, 2, tzinfo=UTC),
            id = "only-a-source-distribution"
        ),
        param({"wheels": [{"url": "a"}]}, None, id="the-index-names-no-time"),
        param({}, None, id="no-file")
    ]
)
def test_a_locked_package_is_dated_by_its_first_upload(
    files    : dict[str, object],
    released : datetime | None
):
    """
    Pins the date a release takes across the files the lockfile names.
    """
    package = PylockPackage.model_validate({"name": "a", "version": "1"} | files)

    assert package.released == released


def test_a_read_gathers_every_report_beside_the_alerts_and_the_holds(
    checkout    : Callable[[Mapping[str, str]], None],
    fp          : FakeProcess,
    monkeypatch : MonkeyPatch
):
    """
    Pins that the read marks each lift with the alerts it clears and takes
    the holds from the tracked file, each manager keeping its own order.
    """
    checkout({".mise/holds.toml": '[holds]\npython = "the reason"\n'})
    fp.register(ALERTS, stdout=dumps([[alert_of()]]))
    monkeypatch.setattr(Lifts, "managers", (Reporting,))

    lifts = Lifts.read()

    assert [lift.clears for lift in lifts.lifts] == [("GHSA-xmj3-9gf7-h52w",)]
    assert lifts.holds == {"python": "the reason"}


def test_a_repository_pinned_at_two_commits_reads_as_one_lift_per_commit(
    checkout : Callable[[Mapping[str, str]], None],
    tagged   : Callable[[str], None]
):
    """
    Pins that each commit a repository's actions are pinned to takes a row
    of its own, so a write moves both to the latest release's commit.
    """
    other = "c" * 40

    checkout(
        {
            ".github/workflows/ci.yml": dedent(
                f"""\
                name: CI
                on: push
                jobs:
                  check:
                    runs-on: ubuntu-latest
                    steps:
                      - uses: actions/checkout@{PINNED}
                      - uses: actions/checkout@{other}
                """
            )
        }
    )

    for _ in range(2):
        tagged(f"{TARGET}\trefs/tags/v5.0.0\n")

    lifts = ActionLifts.read().lifts

    assert [lift.pinned for lift in lifts] == [PINNED, other]
    assert {lift.target for lift in lifts} == {TARGET}


@mark.parametrize(
    "requirement",
    [
        param("a==2.0.0", id="at-the-newest-release"),
        param("a==3.0.0", id="past-the-resolution"),
        param("a==2.*", id="a-wildcard"),
        param("a>=1", id="a-range"),
        param("a>=1,<3", id="two-specifiers"),
        param("a", id="no-specifier"),
        param("b==1.0.0", id="a-package-the-resolution-leaves-out")
    ]
)
def test_only_an_exact_pin_behind_the_resolution_reads_as_a_lift(
    checkout    : Callable[[Mapping[str, str]], None],
    fp          : FakeProcess,
    manifest    : str,
    requirement : str
):
    """
    Pins each pin the read names no lift for.
    """
    checkout(
        {
            "pyproject.toml": manifest.replace(
                '"packaging==26.3"',
                f'"{requirement}"'
            ).replace('"hatchling==1.32.4"', f'"{requirement}"')
        }
    )
    fp.register([*COMPILE, "-"], stdout=pylock_of(("a", "2.0.0")))

    assert RequirementLifts.read().lifts == ()


def test_a_site_lift_with_no_listed_time_stays_undated(fp: FakeProcess):
    """
    Pins that a release `bun info` lists no time for reads an empty age.
    """
    fp.register(
        ["bun", "info", "oxlint", "time", "--json"],
        stdout = dumps({"created": "2020-01-01T00:00:00Z"})
    )

    assert SiteLifts.dated(lift_of("oxlint 1.0.0 1.2.0")).released is None


def test_a_site_package_named_for_the_deployer_takes_the_manifests_route(
    fp       : FakeProcess,
    tmp_path : Path
):
    """
    Pins that the home of a lift rather than its name decides its route, so
    a `wrangler` in the site's manifest goes through `bun add` and reads no
    deploy step, which `tmp_path` leaves absent.
    """
    fp.register(
        [
            "bun", "add", "--cwd", "docs",
            "--dev", "--exact", "--lockfile-only", "wrangler@4.200.0"
        ]
    )

    SiteLifts(
        lifts = (lift_of("wrangler 4.151.3 4.200.0", home=Path("docs/package.json")),)
    ).write(Checkout(root=tmp_path))

    assert fp.call_count(["bun", "add", fp.any()]) == 1


def test_a_site_write_of_wrangler_alone_runs_no_bun_add(
    checkout : Callable[[Mapping[str, str]], None],
    fp       : FakeProcess,
    tmp_path : Path
):
    """
    Pins that a lift touching no site package leaves `bun` unstarted, which
    `fp` enforces by refusing any unregistered command.
    """
    path = Path(".github/workflows/pages.yml")

    checkout({str(path): WORKFLOW})

    SiteLifts(
        lifts = (lift_of("wrangler 4.151.3 4.200.0", home=path),)
    ).write(
        Checkout(root=tmp_path)
    )

    assert not list(fp.calls)


@mark.parametrize(
    ("tags", "followed"),
    [
        param(
            {"latest": "1.6.4", "next": "2.0.0-alpha.21"},
            "2.0.0-alpha.21",
            id = "the-next-tag-past-the-pin"
        ),
        param(
            {"latest": "2.0.0", "next": "2.0.0-rc.1"},
            "2.0.0",
            id = "the-stable-release-once-it-passes-the-next-tag"
        ),
        param({"latest": "1.6.4"}, "2.0.0-alpha.20", id="no-tag-past-the-pin"),
        param(
            {"latest": "1.6.4", "next": "2.0.0-alpha.20"},
            "2.0.0-alpha.20",
            id = "the-pin-itself"
        ),
        param(
            {"canary": "not-a-version", "latest": "1.6.4"},
            "2.0.0-alpha.20",
            id = "a-tag-naming-no-version"
        )
    ]
)
def test_a_prerelease_pin_follows_the_highest_dist_tag_at_or_above_it(
    followed : str,
    fp       : FakeProcess,
    tags     : dict[str, str]
):
    """
    Pins the version a prerelease pin moves to, given every dist-tag the
    package carries.
    """
    fp.register(
        ["bun", "info", "vitepress", "dist-tags", "--json"],
        stdout = dumps(tags)
    )

    assert SiteLifts.followed("vitepress", "2.0.0-alpha.20") == followed


def test_a_site_write_pins_each_package_and_the_deploy_step(
    checkout : Callable[[Mapping[str, str]], None],
    fp       : FakeProcess,
    tmp_path : Path
):
    """
    Pins that the packages go through one `bun add` writing the manifest and
    the lockfile, and that the Wrangler release lands in the deploy step.
    """
    path = Path(".github/workflows/pages.yml")

    checkout({str(path): WORKFLOW})
    fp.register(
        [
            "bun", "add", "--cwd", "docs", "--dev",
            "--exact", "--lockfile-only", "oxlint@1.2.0", "vitepress@2.0.0-alpha.21"
        ]
    )

    SiteLifts(
        lifts = (
            lift_of("oxlint 1.0.0 1.2.0", home=Path("docs/package.json")),
            lift_of(
                pin  = "vitepress 2.0.0-alpha.20 2.0.0-alpha.21",
                home = Path("docs/package.json")
            ),
            lift_of("wrangler 4.151.3 4.200.0", home=path)
        )
    ).write(Checkout(root=tmp_path))

    assert "wranglerVersion : 4.200.0\n" in (tmp_path / path).read_text(
        encoding = "utf-8"
    )


def test_a_write_stops_at_the_first_command_failing(fp: FakeProcess, tmp_path: Path):
    """
    Pins that a failing `mise lock` ends the write before any install.
    """
    fp.register(["mise", "lock"], returncode=1)

    with raises(CalledProcessError):
        lifts_of(lift_of("uv 0.12.13 0.13.0")).write(Checkout(root=tmp_path))

    assert [list(call) for call in fp.calls] == [["mise", "lock"]]


def test_an_action_at_its_latest_release_reads_as_no_lift(
    tagged: Callable[[str], None]
):
    """
    Pins that a pin on the commit the latest tag names is no lift, whichever
    name the tag carries.
    """
    tagged(f"{PINNED}\trefs/tags/v5.0.0\n")

    assert ActionLift.read(pinned=PINNED, repository="actions/checkout") is None


@mark.parametrize(
    ("tags", "current"),
    [
        param(
            {"v4": PINNED, "v4.2": PINNED, "v4.2.2": PINNED},
            "v4.2.2",
            id = "the-highest-version-naming-the-commit"
        ),
        param({"latest": PINNED}, PINNED, id="a-tag-naming-no-version"),
        param({"v3": "c" * 40}, PINNED, id="no-tag-naming-the-commit")
    ]
)
def test_an_action_lift_reads_its_current_version_from_the_tags_naming_its_commit(
    current : str,
    tagged  : Callable[[str], None],
    tags    : dict[str, str]
):
    """
    Pins the version a commit pin reads as, and that the lift moves it to
    the commit the latest release's tag names, dated by that release.
    """
    tagged(
        "".join(
            f"{commit}\trefs/tags/{tag}\n"
            for tag, commit in (tags | {"v5.0.0": TARGET}).items()
        )
    )

    lift = ActionLift.read(pinned=PINNED, repository="actions/checkout")

    assert (lift.current, lift.newest, lift.target) == (current, "v5.0.0", TARGET)
    assert lift.released == datetime(2026, 10, 1, tzinfo=UTC)
    assert lift.home == Path(".github")


def test_an_action_write_moves_the_commit_in_every_file_naming_it(
    checkout : Callable[[Mapping[str, str]], None],
    tmp_path : Path
):
    """
    Pins that the write reaches each workflow and the composite action, and
    leaves a commit it does not name as it stands.
    """
    other    = "c" * 40
    action   = Path(".github/actions/provision/action.yml")
    workflow = Path(".github/workflows/ci.yml")

    checkout(
        {
            str(action): dedent(
                f"""\
                name: Provision
                description: Provisions.
                runs:
                  using: composite
                  steps:
                    - uses: actions/checkout@{PINNED}
                """
            ),

            str(workflow): dedent(
                f"""\
                name: CI
                on: push
                jobs:
                  check:
                    runs-on: ubuntu-latest
                    steps:
                      - uses: actions/checkout@{PINNED}
                      - uses: other/action@{other}
                """
            )
        }
    )

    ActionLifts(
        lifts = (
            ActionLift(
                current = "v4",
                home    = Path(".github"),
                name    = "actions/checkout",
                newest  = "v5",
                pinned  = PINNED,
                target  = TARGET
            ),
        )
    ).write(Checkout(root=tmp_path))

    written = (tmp_path / workflow).read_text(encoding="utf-8")

    assert f"actions/checkout@{TARGET}" in (tmp_path / action).read_text(
        encoding = "utf-8"
    )
    assert f"actions/checkout@{TARGET}" in written
    assert f"other/action@{other}" in written


def test_an_alert_list_reads_every_page_of_open_alerts(fp: FakeProcess):
    """
    Pins the request for open alerts and that the pages `--slurp` nests read
    as one list, each alert reading the fields Dependabot nests.
    """
    fp.register(ALERTS, stdout=dumps([[alert_of()], [alert_of(patched=None)]]))

    first, second = Alert.listed()

    assert (first.advisory, first.ecosystem, first.package, first.patched) == (
        "GHSA-xmj3-9gf7-h52w", "pip", "setuptools",
        Version("84.1.0")
    )
    assert second.patched is None


def test_an_annotated_tag_names_the_commit_it_peels_to(tagged: Callable[[str], None]):
    """
    Pins that the `^{}` line `git ls-remote` prints for an annotated tag,
    which follows the line naming the tag's own object, decides its commit.
    """
    tagged(
        f"{'c' * 40}\trefs/tags/v4.2.2\n{PINNED}\trefs/tags/v4.2.2^{{}}\n"
        f"{'d' * 40}\trefs/tags/v5.0.0\n{TARGET}\trefs/tags/v5.0.0^{{}}\n"
    )

    lift = ActionLift.read(pinned=PINNED, repository="actions/checkout")

    assert (lift.current, lift.target) == ("v4.2.2", TARGET)


def test_an_exact_pin_lift_writes_only_the_pin_it_names(
    checkout : Callable[[Mapping[str, str]], None],
    tmp_path : Path
):
    """
    Pins that a lift writes over the exact pin in the file declaring it,
    leaving a pin of another package with the same version as it stands.
    """
    checkout({"file": '["a==1.0.0", "b==1.0.0"]\n'})

    RequirementLifts(
        lifts = (lift_of("a 1.0.0 2.0.0", home=Path("file")),)
    ).write(Checkout(root=tmp_path))

    assert (tmp_path / "file").read_text(
        encoding = "utf-8"
    ) == '["a==2.0.0", "b==1.0.0"]\n'


@mark.parametrize(
    ("versions", "highest"),
    [
        param("v1.2.3", "1.2.3", id="one-version"),
        param("v2.14.1, v2.14.1+cpu", "2.14.1", id="a-local-build-across-platforms"),
        param("v1.9.0, v1.10.0", "1.10.0", id="compared-as-versions-rather-than-text")
    ]
)
def test_the_dry_run_reads_the_highest_public_version_it_lists(
    highest  : str,
    versions : str
):
    """
    Pins how a package whose resolution forks across platforms reads.
    """
    assert PackageLifts.highest(versions) == highest


def test_concurrently_returns_each_result_in_the_order_of_its_items():
    """
    Pins that the pool's results follow the items rather than the order the
    threads finish in.
    """
    assert concurrently([3, 1, 2], str) == ["3", "1", "2"]


def test_each_action_repository_reads_once_across_every_workflow_and_manifest(
    checkout : Callable[[Mapping[str, str]], None],
    tagged   : Callable[[str, str], None]
):
    """
    Pins that a step in a workflow, a step in the composite action, and a
    sub-action under one repository read as one lift of that repository, in
    the order of its name, and that a local action names none.
    """
    checkout(
        {
            ".github/actions/provision/action.yml": dedent(
                f"""\
                name: Provision
                description: Provisions.
                runs:
                  using: composite
                  steps:
                    - uses: actions/checkout@{PINNED}
                    - uses: github/codeql-action/upload-sarif@{PINNED}
                """
            ),

            ".github/workflows/ci.yml": dedent(
                f"""\
                name: CI
                on: push
                jobs:
                  check:
                    runs-on: ubuntu-latest
                    steps:
                      - uses: actions/checkout@{PINNED}
                      - uses: ./.github/actions/provision
                """
            )
        }
    )

    for repository in ("actions/checkout", "github/codeql-action"):
        tagged(f"{TARGET}\trefs/tags/v5.0.0\n", repository)

    assert [lift.name for lift in ActionLifts.read().lifts] == [
        "actions/checkout", "github/codeql-action"
    ]


def test_holding_leaves_out_only_the_lifts_it_names():
    """
    Pins that a held pin's lift drops out, on a manager and on the whole.
    """
    lifts = lifts_of(lift_of("a 1.0.0 2.0.0"), lift_of("b 1.0.0 2.0.0"))

    assert [lift.name for lift in lifts.holding({"a"}).lifts] == ["b"]
    assert [lift.name for lift in lifts.lifts] == ["a", "b"]


def test_the_exact_pins_lag_the_resolution_of_each_group(
    checkout : Callable[[Mapping[str, str]], None],
    fp       : FakeProcess,
    manifest : str,
    tmp_path : Path
):
    """
    Pins the build requirement, the build constraint resolved beside it, and
    a script's dependency each reading as a lift in the file declaring it,
    each dated by the release's first upload, in the order of their groups.
    A script declaring no dependency resolves nothing.
    """
    scripts = QUIET | {".mise/tasks/repo/tool.py": SCRIPT}

    checkout(scripts | {"pyproject.toml": manifest})

    for script in scripts:
        (tmp_path / script).chmod(0o755)

    fp.register(
        [*COMPILE, "-"],
        occurrences = 2,
        stdout      = pylock_of(
            ("hatchling", "1.33.0"),
            ("packaging", "26.4"),
            ("pyyaml", "6.0.3")
        )
    )

    lifts = RequirementLifts.read().lifts

    assert [(lift.home, lift.name, lift.current, lift.newest) for lift in lifts] == [
        (Path("pyproject.toml"), "hatchling", "1.32.4", "1.33.0"),
        (Path("pyproject.toml"), "packaging", "26.3", "26.4"),
        (Path(".mise/tasks/repo/tool.py"), "pyyaml", "6.0.2", "6.0.3")
    ]
    assert lifts[0].released == datetime(2026, 10, 1, tzinfo=UTC)


def test_the_holds_read_each_pin_beside_its_reason(
    checkout: Callable[[Mapping[str, str]], None]
):
    """
    Pins that the record reads the `[holds]` table of `.mise/holds.toml`.
    """
    checkout({".mise/holds.toml": '[holds]\nuv = "the reason"\n'})

    assert Holds.read().reasons == {"uv": "the reason"}


def test_the_locked_packages_read_each_update_the_dry_run_names(fp: FakeProcess):
    """
    Pins that each `Update` line reads as a lift of `uv.lock`, dated through
    the lockfile compiled for the newest releases alone, whereas a line
    adding or removing a package names none.
    """
    fp.register(
        ["uv", "lock", "--color", "never", "--dry-run", "--no-locked", "--upgrade"],
        stderr = dedent(
            """\
            Resolved 143 packages in 12ms
            Add onnx v1.0.0
            Remove old-package v0.1.0
            Update setuptools v84.0.0 -> v84.2.1
            Update torch v2.14.1, v2.14.1+cpu -> v2.15.0, v2.15.0+cpu
            """
        )
    )
    fp.register(
        [*COMPILE, "--no-deps", "-"],
        stdout = pylock_of(("setuptools", "84.2.1"), ("torch", "2.15.0"))
    )

    lifts = PackageLifts.read().lifts

    assert [(lift.name, lift.current, lift.newest) for lift in lifts] == [
        ("setuptools", "84.0.0", "84.2.1"),
        ("torch", "2.14.1", "2.15.0")
    ]
    assert lifts[0].released == datetime(2026, 10, 1, tzinfo=UTC)


def test_the_shipped_holds_keep_python_on_its_minor_for_the_cp315_wheels(
    monkeypatch  : MonkeyPatch,
    pytestconfig : Config
):
    """
    Pins that the repository holds `python` from the start, with a reason
    naming the `cp315` wheels of `torch` the move waits on.
    """
    monkeypatch.chdir(pytestconfig.rootpath)

    reason = Holds.read().reasons["python"]

    assert "cp315" in reason and "torch" in reason


@mark.parametrize(
    ("lift", "lines"),
    [
        param(
            lift_of("mise 2026.9.18 2026.10.25"),
            [(".mise/config.toml", 'min_version = "2026.10.25"')],
            id = "mise-as-the-floor"
        ),
        param(
            lift_of("uv 0.12.13 0.13.0"),
            [
                (".mise/config.toml", 'uv     = "0.13.0"'),
                ("pyproject.toml", 'required-version              = "==0.13.0"')
            ],
            id = "uv-beside-its-required-version"
        ),
        param(
            lift_of("node 26.12.1 26.13.0"),
            [(".mise/config.toml", 'node   = "26.13.0"')],
            id = "a-tool-with-one-home"
        ),
        param(
            lift_of("python 3.14.6 3.14.10"),
            [
                (".mise/config.toml", 'python = "3.14.10"'),
                (".mise/tasks/repo/tool.py", '# requires-python = ">=3.14"'),
                ("pyproject.toml", 'requires-python = ">=3.14"')
            ],
            id = "python-within-its-minor"
        ),
        param(
            lift_of("python 3.14.6 3.15.1"),
            [
                (".mise/config.toml", 'python = "3.15.1"'),
                (".mise/tasks/repo/tool.py", '# requires-python = ">=3.15"'),
                ("pyproject.toml", 'requires-python = ">=3.15"'),
                ("pyproject.toml", 'target-version = "3.15"')
            ],
            id = "python-to-another-minor"
        )
    ]
)
def test_a_tool_write_reaches_every_home_audit_holds_the_pin_to(
    checkout    : Callable[[Mapping[str, str]], None],
    lift        : Lift,
    lines       : list[tuple[str, str]],
    manifest    : str,
    mise_config : str,
    tmp_path    : Path
):
    """
    Pins each line a lifted tool leaves in each file repeating it, a script
    declaring no `requires-python` staying as it stands.
    """
    scripts = QUIET | {".mise/tasks/repo/tool.py": SCRIPT}

    checkout(
        scripts | {".mise/config.toml": mise_config, "pyproject.toml": manifest}
    )

    for script in scripts:
        (tmp_path / script).chmod(0o755)

    ToolLifts(lifts=(lift,)).write(Checkout(root=tmp_path))

    for path, line in lines:
        assert line in (tmp_path / path).read_text(encoding="utf-8")

    for script, written in QUIET.items():
        assert (tmp_path / script).read_text(encoding="utf-8") == written


def test_the_site_lags_the_latest_release_bun_draws_for_each_pin(
    checkout : Callable[[Mapping[str, str]], None],
    fp       : FakeProcess
):
    """
    Pins that a pin reads the `Latest` cell of its row, a prerelease pin the
    dist-tag it follows, and the Wrangler pin its `latest` dist-tag, whereas
    a pin in no row or at its newest release names no lift, and that the
    report dates each lift.
    """
    checkout(
        {
            ".github/workflows/pages.yml" : WORKFLOW,
            "docs/package.json"           : SITE
        }
    )
    fp.register(
        ["bun", "outdated"],
        stdout = dedent(
            """\
            |--------------------------------------------------------|
            | Package                    | Current | Update | Latest |
            |----------------------------|---------|--------|--------|
            | @types/node (dev)          | 26.6.5  | 26.6.5 | 26.7.0 |
            |----------------------------|---------|--------|--------|
            | oxlint (dev)               | 1.0.0   | 1.0.0  | 1.2.0  |
            |----------------------------|---------|--------|--------|
            | vitepress (dev)            | 2.0.0-alpha.20 | 2.0.0-alpha.20 | 1.6.4 |
            |----------------------------|---------|--------|--------|
            """
        )
    )
    fp.register(
        ["bun", "info", "vitepress", "dist-tags", "--json"],
        stdout = dumps({"latest": "1.6.4", "next": "2.0.0-alpha.21"})
    )
    fp.register(
        ["bun", "info", "wrangler", "dist-tags", "--json"],
        stdout = dumps({"latest": "4.200.0"})
    )

    for name, newest in (
        ("@types/node", "26.7.0"),
        ("oxlint", "1.2.0"),
        ("vitepress", "2.0.0-alpha.21"),
        ("wrangler", "4.200.0")
    ):
        fp.register(
            ["bun", "info", name, "time", "--json"],
            stdout = dumps(
                {"created": "2020-01-01T00:00:00Z", newest: "2026-10-01T00:00:00Z"}
            )
        )

    lifts = SiteLifts.read().lifts

    assert [(lift.home, lift.name, lift.current, lift.newest) for lift in lifts] == [
        (Path("docs/package.json"), "@types/node", "26.6.5", "26.7.0"),
        (Path("docs/package.json"), "oxlint", "1.0.0", "1.2.0"),
        (Path("docs/package.json"), "vitepress", "2.0.0-alpha.20", "2.0.0-alpha.21"),
        (Path(".github/workflows/pages.yml"), "wrangler", "4.151.3", "4.200.0")
    ]
    assert {lift.released for lift in lifts} == {datetime(2026, 10, 1, tzinfo=UTC)}


@mark.parametrize(
    ("attempt", "sentence"),
    [
        param(
            Attempt(held=None, log=Path("whole.log"), passed=True),
            "The whole lift passes mise ci, as whole.log records",
            id = "whole-passing"
        ),
        param(
            Attempt(
                held   = lift_of("uv 0.12.13 0.13.0"),
                log    = Path("without-uv.log"),
                passed = False
            ),
            "The lift holding uv at 0.12.13 fails mise ci, as without-uv.log records",
            id = "holding-one-back-failing"
        )
    ]
)
def test_an_attempt_says_what_it_found_and_where_its_log_sits(
    attempt  : Attempt,
    sentence : str
):
    """
    Pins the sentence a trial prints as each attempt ends.
    """
    assert attempt.sentence == sentence


@mark.parametrize(
    ("passed", "status", "verdict"),
    [
        param([True], 0, "Every lift not held passes mise ci", id="whole-passes"),
        param(
            [False, False, True],
            1,
            "The lift breaking the tree is b 2.0.0",
            id = "one-major-lift-breaks-it"
        ),
        param(
            [False, True, True],
            1,
            "The lift breaking the tree is a 2.0.0, b 2.0.0",
            id = "either-major-lift-breaks-it"
        ),
        param(
            [False, False, False],
            1,
            "No major lift held back alone lets mise ci pass",
            id = "no-one-major-lift-breaks-it"
        ),
        param(
            [False],
            1,
            "No major lift held back alone lets mise ci pass",
            id = "no-major-lift-to-hold-back"
        )
    ]
)
def test_a_trial_names_the_lift_breaking_the_tree(
    passed  : list[bool],
    status  : int,
    verdict : str
):
    """
    Pins the verdict and the exit status for each result the attempts reach,
    a lift being named where holding it back alone lets `mise ci` pass.
    """
    held  = [None, lift_of("a 1.0.0 2.0.0"), lift_of("b 1.0.0 2.0.0")]
    trial = Trial(
        attempts = tuple(
            Attempt(held=lift, log=Path("log"), passed=result)
            for lift, result in zip(held, passed, strict=False)
        )
    )

    assert (trial.status, trial.verdict) == (status, verdict)


@mark.parametrize(
    ("lift", "rebuilt"),
    [
        param(lift_of("uv 0.12.13 0.13.0"), [], id="no-rebuild"),
        param(
            lift_of("python 3.14.6 3.15.1"),
            [
                ["mise", "x", "--", "uv", "venv", "--clear"],
                ["mise", "x", "--", "uv", "sync"]
            ],
            id = "rebuild-on-the-interpreter-the-lift-pins"
        ),
        param(
            lift_of("python 3.14.6 3.14.10"),
            [
                ["mise", "x", "--", "uv", "venv", "--clear"],
                ["mise", "x", "--", "uv", "sync"]
            ],
            id = "rebuild-within-the-minor"
        )
    ]
)
def test_a_write_locks_installs_and_syncs_after_every_manager_writes(
    fp       : FakeProcess,
    lift     : Lift,
    rebuilt  : list[list[str]],
    tmp_path : Path
):
    """
    Pins the order of the commands once the managers write, and the two that
    build `.venv` again where `python` moves.
    """
    commands = [["mise", "lock"], ["mise", "install"], ["mise", "run", "lock:sync"]]

    for command in [*commands, *rebuilt]:
        fp.register(command)

    lifts_of(lift).write(Checkout(root=tmp_path))

    assert (tmp_path / "lifted.txt").read_text(encoding="utf-8") == lift.name
    assert [list(call) for call in fp.calls] == [*commands, *rebuilt]


def test_the_table_prints_one_markdown_row_per_lift(snapshot: SnapshotAssertion):
    """
    Pins the columns a row gives, an empty cell for a release no manager
    dates, and the shape that pastes into a pull request as it prints.
    """
    now = datetime.now(UTC)

    table = lifts_of(
        lift_of(
            clears   = ("GHSA-xmj3-9gf7-h52w", "GHSA-other"),
            pin      = "setuptools 84.0.0 84.2.1",
            released = now - timedelta(days=12, hours=1)
        ),
        lift_of("python 3.14.6 3.15.1", home=Path(".mise/config.toml")),
        lift_of(
            pin      = f"actions/checkout {PINNED} v5.0.0",
            home     = Path(".github"),
            released = now - timedelta(hours=1)
        )
    ).table

    assert table_text(table) == snapshot


@mark.parametrize(
    ("held", "log", "returncode", "passed"),
    [
        param(None, "whole.log", 0, True, id="whole-passing"),
        param(None, "whole.log", 1, False, id="whole-failing"),
        param(
            lift_of("actions/checkout v4 v5", home=Path(".github")),
            "without-actions-checkout.log",
            0,
            True,
            id = "holding-back-a-repository"
        )
    ]
)
def test_an_attempt_runs_ci_in_a_clone_it_removes_and_keeps_its_log(
    clone       : Path,
    fp          : FakeProcess,
    held        : Lift | None,
    log         : str,
    monkeypatch : MonkeyPatch,
    passed      : bool,
    returncode  : int
):
    """
    Pins that the lift lands in the scratch clone rather than the checkout,
    that the clone is gone once the attempt ends, and that the log, named
    for what the attempt holds back, keeps what each command printed.
    """
    scratch = clone / "data/scratch"
    scratch.mkdir(parents=True)
    monkeypatch.setattr("tempfile.tempdir", str(scratch))
    fp.pass_command(["git", fp.any()], occurrences=4)

    for command in (
        ["mise", "lock"],
        ["mise", "install"],
        ["mise", "run", "lock:sync"]
    ):
        fp.register(command)

    fp.register(
        ["mise", "run", "--continue-on-error", "repo:ci"],
        returncode = returncode,
        stdout     = "the suite printed\n"
    )

    attempt = lifts_of(lift_of("uv 0.12.13 0.13.0")).attempt(
        held,
        clone / "data/lift"
    )

    assert attempt.passed is passed
    assert attempt.held == held
    assert attempt.log == clone / "data/lift" / log
    assert "the suite printed" in attempt.log.read_text(encoding="utf-8")
    assert not (clone / "lifted.txt").exists()
    assert not list(scratch.iterdir())


@mark.parametrize(
    ("lift", "mise_lock", "printed"),
    [
        param(
            lift_of("uv 0.12.13 0.13.0"),
            1,
            str(CalledProcessError(1, ("mise", "lock"))),
            id = "a-command-failing"
        ),
        param(
            lift_of("broken 1.0.0 2.0.0"),
            0,
            "`uv.lock` matches nothing",
            id = "a-home-refusing-the-write"
        )
    ]
)
def test_an_attempt_whose_write_fails_records_the_error_as_failing(
    clone     : Path,
    fp        : FakeProcess,
    lift      : Lift,
    mise_lock : int,
    printed   : str
):
    """
    Pins that a write failing either way ends the attempt as failed, with
    the error in its log rather than ending the task.
    """
    fp.pass_command(["git", fp.any()], occurrences=4)
    fp.register(["mise", "lock"], returncode=mise_lock)

    attempt = lifts_of(lift).attempt(None, clone / "data/lift")

    assert attempt.passed is False
    assert printed in attempt.log.read_text(encoding="utf-8")


@mark.parametrize(
    ("passes", "attempted"),
    [
        param({None: True}, [None], id="a-passing-lift-holds-nothing-back"),
        param(
            {"a": True, None: False},
            [None, "a"],
            id = "a-failing-lift-holds-back-each-major-lift-in-turn"
        )
    ]
)
def test_a_trial_holds_back_each_major_lift_only_after_the_whole_lift_fails(
    attempted   : list[str | None],
    capsys      : CaptureFixture[str],
    monkeypatch : MonkeyPatch,
    passes      : dict[str | None, bool]
):
    """
    Pins the attempts a trial runs, in order, holding back only a major lift
    and a pin two major rows name just once, and that each attempt prints
    its sentence as it ends.
    """
    ran = []

    def attempt(_: Lifts, held: Lift | None, logs: Path) -> Attempt:
        """
        Records the lift held back and reads its result from `passes`.
        """
        name = held.name if held else None
        ran.append(name)

        return Attempt(held=held, log=logs / "log", passed=passes[name])

    monkeypatch.setattr(Lifts, "attempt", attempt)

    lifts = lifts_of(
        lift_of("a 1.0.0 2.0.0"),
        lift_of("a 1.0.0 2.0.0", home=Path("pyproject.toml")),
        lift_of("b 1.0.0 1.1.0")
    )
    trial = lifts.tried(Path("logs"))

    assert ran == attempted
    assert [attempt.held for attempt in trial.attempts] == [
        lifts.lifts[1] if name else None for name in attempted
    ]
    assert capsys.readouterr().out.splitlines() == [
        attempt.sentence for attempt in trial.attempts
    ]


@mark.parametrize(
    ("trying", "writing", "passing", "status", "tried", "wrote"),
    [
        param(False, False, True, 0, False, False, id="report-alone"),
        param(True, False, True, 0, True, False, id="try-alone"),
        param(False, True, True, 0, False, True, id="write-alone"),
        param(True, True, True, 0, True, True, id="write-after-a-passing-trial"),
        param(True, True, False, 1, True, False, id="no-write-after-a-failing-trial"),
        param(True, False, False, 1, True, False, id="try-failing-alone")
    ]
)
def test_a_lift_tries_and_writes_as_its_flags_ask(
    monkeypatch : MonkeyPatch,
    passing     : bool,
    status      : int,
    tmp_path    : Path,
    tried       : bool,
    trying      : bool,
    wrote       : bool,
    writing     : bool
):
    """
    Pins the exit status and the two steps each flag runs, the write running
    only after a passing trial where both are given.
    """
    calls = []

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        Lifts,
        "tried",
        lambda self, logs: calls.append(("tried", logs)) or Trial(
            attempts = (Attempt(held=None, log=logs / "whole.log", passed=passing),)
        )
    )
    monkeypatch.setattr(
        Lifts,
        "write",
        lambda self, checkout: calls.append(("wrote", checkout.root))
    )

    lifts = lifts_of(lift_of("uv 0.12.13 0.13.0"))

    assert lifts.lift(held=(), trying=trying, writing=writing) == status
    assert calls == [
        *([("tried", Path(".cache/lift"))] if tried else []),
        *([("wrote", tmp_path)] if wrote else [])
    ]


def test_the_tools_read_each_entry_naming_a_newer_release_beside_the_floor(
    checkout    : Callable[[Mapping[str, str]], None],
    fp          : FakeProcess,
    mise_config : str
):
    """
    Pins the two reports `mise outdated` gives, the project's and the
    floor's under the `aqua:` name it takes, each in the order of the name
    mise gives it. An entry naming no bump is left out, and a release `mise
    ls-remote` lists no time for reads an empty age.
    """
    checkout({".mise/config.toml": mise_config})
    fp.register(
        ["mise", "outdated", "--bump", "--json", "--local"],
        stdout = dumps(
            {
                "node" : {"bump": None, "requested": "26.12.1"},
                "uv"   : {"bump": "0.13.0", "requested": "0.12.13"}
            }
        )
    )
    fp.register(
        ["mise", "outdated", "--bump", "--json", "aqua:jdx/mise@2026.9.18"],
        stdout = dumps(
            {"aqua:jdx/mise": {"bump": "2026.10.25", "requested": "2026.9.18"}}
        )
    )
    fp.register(
        ["mise", "ls-remote", "--json", "aqua:jdx/mise", "2026.10.25"],
        stdout = dumps([{"version": "2026.10.25"}])
    )
    fp.register(
        ["mise", "ls-remote", "--json", "uv", "0.13.0"],
        stdout = dumps(
            [
                {"created_at": "2026-01-01T00:00:00Z", "version": "0.13.0-rc.1"},
                {"created_at": "2026-10-01T00:00:00Z", "version": "0.13.0"}
            ]
        )
    )

    floor, uv = ToolLifts.read().lifts

    assert (floor.name, floor.current, floor.newest, floor.released) == (
        "mise", "2026.9.18", "2026.10.25", None
    )
    assert (uv.name, uv.current, uv.newest, uv.released) == (
        "uv", "0.12.13", "0.13.0",
        datetime(2026, 10, 1, tzinfo=UTC)
    )
    assert uv.home == Path(".mise/config.toml")


@mark.parametrize(
    ("holds", "held", "named"),
    [
        param({}, ("nope",), "nope", id="a-run-hold-the-table-does-not-list"),
        param(
            {"nope": "the reason"},
            (),
            "nope",
            id = "a-file-hold-the-table-does-not-list"
        ),
        param(
            {"z": "the reason"},
            ("nope",),
            "nope, z",
            id = "every-unlisted-name-in-sorted-order"
        )
    ]
)
@mark.usefixtures("refused")
def test_a_hold_naming_no_listed_pin_exits_2_before_any_trial_or_write(
    capsys : CaptureFixture[str],
    held   : tuple[str, ...],
    holds  : dict[str, str],
    named  : str
):
    """
    Pins status 2 for a name the table does not list, along either route,
    with neither step running and the message on standard error.
    """
    lifts = lifts_of(lift_of("a 1.0.0 2.0.0"), holds=holds)

    assert lifts.lift(held=held, trying=True, writing=True) == 2
    assert f"no pin named {named} to hold" in capsys.readouterr().err


@mark.parametrize(
    ("lifts", "printed"),
    [
        param(
            lifts_of(),
            "Every pin stands at its newest release\n",
            id = "no-lift-at-all"
        ),
        param(
            lifts_of(lift_of("a 1.0.0 2.0.0"), holds={"a": "the reason"}),
            "Leaving a at 1.0.0, because the reason\n",
            id = "every-lift-held"
        )
    ]
)
@mark.usefixtures("refused")
def test_a_lift_with_nothing_left_to_lift_neither_tries_nor_writes(
    capsys  : CaptureFixture[str],
    lifts   : Lifts,
    printed : str
):
    """
    Pins that no scratch clone and no lockfile run starts where nothing
    remains to lift, which the status and the output report plainly.
    """
    assert lifts.lift(held=(), trying=True, writing=True) == 0
    assert capsys.readouterr().out.endswith(printed)


def test_the_tools_write_after_every_manager_that_runs_uv():
    """
    Pins that `ToolLifts` writes last, since it moves the `required-version`
    every `uv` command an earlier manager starts runs under.
    """
    assert Lifts.managers[-1] is ToolLifts
