"""
Defines what the `repo:lift` task reads and writes, meaning `Lift`, one
pin beside the newest release of what it pins, and each `Manager` reading
one kind of pin through the commands of the tool that resolves it. `Lifts`
gathers every manager's lifts into the table the task prints, then tries all
but the pins `Holds` keeps in a scratch clone as a `Trial` and writes them
into a `Checkout`.
"""

from abc                import ABC, abstractmethod
from collections.abc    import Callable, Collection, Iterable
from concurrent.futures import ThreadPoolExecutor
from datetime           import UTC, datetime
from io                 import TextIOBase
from itertools          import chain
from operator           import attrgetter, methodcaller
from os                 import environ, pathsep
from packaging.requirements import Requirement
from packaging.utils        import canonicalize_name
from packaging.version      import InvalidVersion, Version
from pathlib                import Path
from pydantic               import AliasPath, Field, InstanceOf, TypeAdapter
from re           import escape, finditer, subn
from rich.box     import MARKDOWN
from rich.console import Console
from rich.table   import Table
from shutil       import copy2
from subprocess   import CalledProcessError, check_output, run
from sysconfig    import get_path
from tempfile     import TemporaryDirectory
from tomllib      import loads
from typing       import ClassVar, Self, TypeForm

from squirtl.emulator.schemas import Record
from squirtl.releases.schemas import GithubRelease
from squirtl.repo.checks      import SitePins
from squirtl.repo.github      import Command
from squirtl.repo.schemas     import (
    Actions, LockedPackage, Lockfile, Manifest, MiseConfig, Scripts, SiteManifest, TomlFile,
    VersionNumber, Workflow, Workflows
)


def concurrently[T, R](items: Iterable[T], work: Callable[[T], R]) -> list[R]:
    """
    Runs `work` over each of `items` on a pool of threads, since each call
    waits on a registry or on a tool's report.

    Returns:
        The results, in the order of `items`.
    """
    with ThreadPoolExecutor() as pool:
        return list(pool.map(work, items))


def parsed[T](shape: TypeForm[T], *command: str, cwd: Path | None = None) -> T:
    """
    Runs `command`, in `cwd` where it names a folder, and validates what it
    prints to standard output as JSON against `shape`.
    """
    return TypeAdapter(shape).validate_json(check_output(command, cwd=cwd))


class Checkout(Record):
    """
    A checkout a lift is written into, beside the variables each command
    there runs under and the log it prints into. A command takes the task's
    own variables where `env` is `None` and prints to the terminal where
    `log` is `None`.
    """

    root: Path
    """
    The root of the checkout.
    """

    env: dict[str, str] | None = None
    """
    The variables each command runs under.
    """

    log: InstanceOf[TextIOBase] | None = None
    """
    The open file each command prints into.
    """

    uv_run: ClassVar[frozenset[str]] = frozenset(
        {"UV", "UV_RUN_RECURSION_DEPTH", "VIRTUAL_ENV"}
    )
    """
    The variables `uv run` sets for the task it starts in the checkout's
    `.venv`.
    """

    @staticmethod
    def assigned(current: str, key: str, prefix: str = "") -> str:
        """
        Builds the pattern `respell` uses to find the version `current` on
        the line assigning `key`. That line assigns through `=` in TOML or
        `:` in YAML, may open on the `# ` of a script's inline metadata, and
        holds the value quoted or bare, with `prefix` before the version.
        The pattern's first group holds the line up to the version.
        """
        return (
            rf'(?m)^([# ]*{escape(key)} *[=:] *"?{escape(prefix)})'
            rf'{escape(current)}(?="?$)'
        )

    def cloned(self, destination: Path, log: TextIOBase) -> Self:
        """
        Clones the checkout into `destination`, sharing its objects, and
        lays its uncommitted changes and its untracked files over the clone,
        each file `.gitignore` excludes left out, so the clone holds the
        tree as it stands.

        Returns:
            The clone, whose commands print into `log` and run under the
            task's variables with mise trusting the clone's config, less each
            one `uv run` sets and the folder of scripts it puts first on `PATH`.
        """
        scripts = get_path("scripts")

        run(
            ["git", "clone", "--quiet", "--shared", str(self.root), str(destination)],
            check = True
        )

        if changes := check_output(["git", "diff", "--binary", "HEAD"], cwd=self.root):
            run(["git", "apply"], check=True, cwd=destination, input=changes)

        for untracked in check_output(
            ["git", "ls-files", "--exclude-standard", "--others", "-z"],
            cwd  = self.root,
            text = True
        ).split("\0")[:-1]:
            (destination / untracked).parent.mkdir(exist_ok=True, parents=True)
            copy2(self.root / untracked, destination / untracked, follow_symlinks=False)

        return type(self)(
            env = {
                key: value for key, value in environ.items() if key not in self.uv_run
            } | {
                "MISE_TRUSTED_CONFIG_PATHS": str(destination),
                "PATH": pathsep.join(
                    folder
                    for folder in environ["PATH"].split(pathsep)
                    if folder != scripts
                )
            },
            log  = log,
            root = destination
        )

    def respell(self, path: Path, pattern: str, version: str):
        """
        Writes `version` over the one match of the regular expression
        `pattern` in the file at `path` under the root, keeping what the
        pattern's first group holds.

        Raises:
            ValueError: Where `pattern` matches the file other than once,
                        before the file is written.
        """
        file           = self.root / path
        written, times = subn(
            pattern,
            rf"\g<1>{version}",
            file.read_text(encoding="utf-8")
        )

        if times != 1:
            raise ValueError(
                f"`{path}` matches `{pattern}` {times} times rather than once"
            )

        file.write_text(written, encoding="utf-8")

    def run(self, *command: str):
        """
        Runs `command` at the root.

        Raises:
            CalledProcessError: Where it exits nonzero.
        """
        run(
            command,
            check  = True,
            cwd    = self.root,
            env    = self.env,
            stderr = self.log,
            stdout = self.log
        )


def version_of(text: str) -> Version | None:
    """
    Parses `text` as a version, a leading `v` and an npm prerelease suffix
    PEP 440 can read, such as `-alpha.21`, included, or returns `None` where
    it names no version, as a commit, a tag such as `latest`, or a suffix
    such as `-next.3` does.
    """
    try:
        return Version(text)
    except InvalidVersion:
        return None


class Alert(Record, extra="ignore"):
    """
    One open alert Dependabot raises on a vulnerable release of a package
    the repository pins, read for the advisory it names and the first
    release past the vulnerability.
    """

    advisory: str = Field(validation_alias=AliasPath("security_advisory", "ghsa_id"))
    """
    The GitHub Security Advisory ID the alert names.
    """

    ecosystem: str = Field(
        validation_alias = AliasPath("dependency", "package", "ecosystem")
    )
    """
    The name Dependabot gives the package's manager, such as `pip`, `npm`,
    or `actions`.
    """

    package: str = Field(validation_alias=AliasPath("dependency", "package", "name"))
    """
    The name of the vulnerable package.
    """

    patched: VersionNumber | None = Field(
        None,
        validation_alias = AliasPath(
            "security_vulnerability",
            "first_patched_version",
            "identifier"
        )
    )
    """
    The first release past the vulnerability, or `None` where none is
    published yet.
    """

    def clears(self, ecosystem: str | None, lift: Lift) -> bool:
        """
        Tells whether `lift`, of a pin in `ecosystem`, moves the package the
        alert names from below the first release past the vulnerability to
        that release or later.
        """
        return (
            (self.ecosystem, canonicalize_name(self.package))
                == (ecosystem, canonicalize_name(lift.name))
            and (span := lift.span) is not None
            and self.patched        is not None
            and span[0]                  < self.patched <= span[1]
        )

    @classmethod
    def listed(cls) -> list[Self]:
        """
        Reads every open alert through Dependabot's alerts endpoint, one
        page of a hundred at a time.
        """
        return list(
            chain.from_iterable(
                Command.api(
                    "dependabot/alerts",
                    "--paginate",
                    "--slurp",
                    "-f",
                    "per_page=100",
                    "-f",
                    "state=open"
                ).parsed(list[list[cls]])
            )
        )


class HeldPackageMoved(ValueError):
    """
    Raised where `uv lock` leaves a held package off its current release,
    its argument a sentence on each such package, one to a line.
    """


class Holds(TomlFile):
    """
    The pins `file` keeps where they stand on every run of `repo:lift`, each
    beside the reason it stays.
    """

    file: ClassVar[Path] = Path(".mise/holds.toml")

    reasons: dict[str, str] = Field(alias="holds")
    """
    The reason each pin stays, under the pin's name as the table names it,
    written as the clause following `because`.
    """


class MiseRelease(Record, extra="ignore"):
    """
    One release of a tool `mise ls-remote` lists, read for its version and
    when it was published.
    """

    version: str
    """
    The version, as mise writes it.
    """

    created: datetime | None = Field(None, alias="created_at")
    """
    When the release was published, or `None` where the backend names no
    time.
    """


class Lift(Record):
    """
    One pin beside the newest release of what it pins, as the report of the
    tool resolving the pin names the two.
    """

    current: str
    """
    The version the pin holds, or the commit it holds where no tag names
    that commit.
    """

    home: Path
    """
    The file the pin is written in, or the folder holding every file that
    writes it.
    """

    name: str
    """
    What the pin pins, as the table names it and `--hold` takes it.
    """

    newest: str
    """
    The version the lift moves the pin to.
    """

    clears: tuple[str, ...] = ()
    """
    The advisory ID of each open Dependabot alert the lift clears.
    """

    released: datetime | None = None
    """
    When the newest release was published, or `None` where the tool names
    no time.
    """

    @property
    def age(self) -> int | None:
        """
        Counts the whole days since the newest release was published, or
        `None` where the tool names no time.
        """
        return (datetime.now(UTC) - self.released).days if self.released else None

    @property
    def cells(self) -> tuple[str, ...]:
        """
        Writes the row the lift takes in the table `Lifts.table` draws.
        """
        return (
            self.name,
            str(self.home),
            self.current, self.newest,
            "yes" if self.major else "",
            "" if self.age is None else str(self.age),
            ", ".join(self.clears)
        )

    @property
    def floor(self) -> bool:
        """
        Tells whether the pin names the release of mise that `min_version`
        sets.
        """
        return self.name == "mise"

    @property
    def interpreter(self) -> bool:
        """
        Tells whether the pin names the CPython interpreter mise provisions.
        """
        return self.name == "python"

    @property
    def major(self) -> bool:
        """
        Tells whether the lift changes the left-most non-zero part of the
        version, the part a caret range holds in npm's `semver`, or the
        minor of the `python` pin, since each CPython minor takes wheels
        built for an ABI tag of its own. A calendar version moving within
        its year crosses none, and neither does a lift from a commit no
        tag names.
        """
        if (span := self.span) is None:
            return False

        before, after = (version.release for version in span)
        lead          = 1 if self.interpreter else next(
            (place for place, part in enumerate(before) if part),
            len(before) - 1
        )

        return before[:lead + 1] != after[:lead + 1]

    @property
    def span(self) -> tuple[Version, Version] | None:
        """
        Parses the current and the newest version, or returns `None` where
        either names no version.
        """
        before, after = version_of(self.current), version_of(self.newest)
        return (before, after) if before and after else None


class ActionLift(Lift):
    """
    The actions of one GitHub repository the workflows pin by commit, beside
    the commit the tag of the repository's latest release names.
    """

    pinned: str
    """
    The commit every step using the repository's actions pins.
    """

    target: str
    """
    The commit the latest release's tag names.
    """

    @classmethod
    def read(cls, pinned: str, repository: str) -> Self | None:
        """
        Reads the lift of the actions of `repository` from the commit
        `pinned` to the commit its latest release's tag names, or returns
        `None` where the two are one commit. The current version reads as
        the highest version a tag naming `pinned` carries.
        """
        latest = Command(
            arguments = ("api", f"repos/{repository}/releases/latest")
        ).parsed(GithubRelease)
        tags = {
            ref.removeprefix("refs/tags/").removesuffix("^{}"): commit
            for line in check_output(
                ["git", "ls-remote", "--tags", f"https://github.com/{repository}"],
                text = True
            ).splitlines()
            for commit, ref in [line.split("\t")]
        }

        if tags[latest.tag] == pinned:
            return None

        return cls(
            current = max(
                (
                    tag
                    for tag, commit in tags.items()
                    if commit == pinned and version_of(tag)
                ),
                default = pinned,
                key     = Version
            ),
            home     = Workflow.directory.parent,
            name     = repository,
            newest   = latest.tag,
            pinned   = pinned,
            released = latest.published,
            target   = tags[latest.tag]
        )


class Manager(Record, ABC):
    """
    The base of the pins one tool resolves that lag their newest release, as
    the tool's own report names them, which a subclass reads and writes into
    a checkout.
    """

    ecosystem: ClassVar[str | None] = None
    """
    The name Dependabot gives the tool's packages, or `None` for a tool
    whose pins no alert names.
    """

    lifts: tuple[Lift, ...]
    """
    Each pin lagging its newest release, in the order the report names it.
    """

    def clearing(self, alerts: Collection[Alert]) -> Self:
        """
        Copies the manager with each lift naming every alert of `alerts`
        it clears.
        """
        return self.model_copy(
            update = {
                "lifts": tuple(
                    lift.model_copy(
                        update = {
                            "clears": tuple(
                                alert.advisory
                                for alert in alerts
                                if alert.clears(self.ecosystem, lift)
                            )
                        }
                    )
                    for lift in self.lifts
                )
            }
        )

    def holding(self, names: Collection[str]) -> Self:
        """
        Copies the manager with the lift of each pin `names` lists left out,
        so the pin stays where it stands.
        """
        return self.model_copy(
            update = {
                "lifts": tuple(lift for lift in self.lifts if lift.name not in names)
            }
        )

    @classmethod
    @abstractmethod
    def read(cls) -> Self:
        """
        Reads every pin the tool's report names behind its newest release.
        """

    @abstractmethod
    def write(self, checkout: Checkout):
        """
        Writes each lift into every home of its pin in `checkout`.
        """


class OutdatedTool(Record, extra="ignore"):
    """
    One tool `mise outdated --bump` reports, read for the version the config
    requests and the newest release past it.
    """

    requested: str
    """
    The version the config requests.
    """

    bump: str | None = None
    """
    The newest release, or `None` where the request already names it.
    """


class PylockFile(Record, extra="ignore"):
    """
    One file a lockfile in the format PEP 751 sets out names for a package,
    read for when it was uploaded.
    """

    uploaded: datetime | None = Field(None, alias="upload-time")
    """
    When the file was uploaded, or `None` where the index names no time.
    """


class PylockPackage(LockedPackage):
    """
    One package a lockfile in the format PEP 751 sets out pins, read beside
    the files it names.
    """

    sdist: PylockFile | None = None
    """
    The source distribution, or `None` where the release ships none.
    """

    wheels: list[PylockFile] = []
    """
    Each wheel the release ships.
    """

    @property
    def released(self) -> datetime | None:
        """
        Reads when the release's first file was uploaded, or `None` where
        the index names no time for any file.
        """
        return min(
            (
                file.uploaded
                for file in (self.sdist, *self.wheels)
                if file and file.uploaded
            ),
            default = None
        )


class Pylock(Record, extra="ignore"):
    """
    The packages a lockfile in the format PEP 751 sets out pins, as `uv pip
    compile` writes it for the requirements it resolves.
    """

    packages: list[PylockPackage]
    """
    Every package the lockfile pins.
    """

    @property
    def named(self) -> dict[str, PylockPackage]:
        """
        Keys each package by its name, as PEP 503 normalizes it.
        """
        return {canonicalize_name(package.name): package for package in self.packages}

    @classmethod
    def compiled(cls, requirements: Iterable[str], *flags: str) -> Self:
        """
        Resolves `requirements` through `uv pip compile` under `flags`,
        reading the lockfile it writes to standard output.
        """
        return cls.model_validate(
            loads(
                check_output(
                    [
                        "uv", "pip", "compile", "--format",
                        "pylock.toml", "--no-header", "--quiet", "--universal",
                        *flags,
                        "-"
                    ],
                    input = "\n".join(requirements),
                    text  = True
                )
            )
        )


class ActionLifts(Manager):
    """
    The third-party actions each workflow and the composite action pin by
    commit, one lift per repository, read through GitHub's REST API, which
    names the repository's latest release, and `git ls-remote`, which names
    the commit each of its tags points at.
    """

    ecosystem: ClassVar[str | None] = "actions"

    lifts: tuple[ActionLift, ...]
    """
    Each repository whose latest release names another commit than the one
    its actions are pinned to, in the order of its name.
    """

    @classmethod
    def read(cls) -> Self:
        """
        Reads the commit each repository's actions are pinned to out of
        every step of the workflows and the action manifests, then each
        repository's latest release and tags.
        """
        pins = {
            ("/".join(action.split("/")[:2]), commit)
            for _, step in chain(Workflows.read().steps, Actions.read().steps)
            if step.pinned
            for action, commit in [step.pinned]
        }

        return cls(
            lifts = tuple(
                filter(
                    None,
                    concurrently(
                        items = sorted(pins),
                        work  = lambda pin: ActionLift.read(
                            pinned     = pin[1],
                            repository = pin[0]
                        )
                    )
                )
            )
        )

    def write(self, checkout: Checkout):
        """
        Writes each target commit over the pinned one in every workflow and
        action manifest naming it.
        """
        for manifest in chain(Workflows.read().workflows, Actions.read().actions):
            file = checkout.root / manifest.path
            text = file.read_text(encoding="utf-8")

            for lift in self.lifts:
                text = text.replace(f"@{lift.pinned}", f"@{lift.target}")

            file.write_text(text, encoding="utf-8")


class RequirementLifts(Manager):
    """
    The exact requirements no lockfile upgrade moves, meaning the build
    requirement and the build constraints `pyproject.toml` declares and each
    dependency a task script's inline metadata pins. Each reads through the
    lockfile `uv pip compile` writes, which resolves the newest release of
    each beside its dependencies and dates each release it pins.
    """

    ecosystem: ClassVar[str | None] = "pip"

    @classmethod
    def read(cls) -> Self:
        """
        Resolves the build requirements beside the build constraints, and
        each script's dependencies, naming a lift for each exact pin the
        resolution moves past.
        """
        manifest = Manifest.read()
        groups   = [
            (Manifest.file, manifest.build_requirements, manifest.build_constraints),
            *(
                (script.path, script.metadata.dependencies)
                for script in Scripts.read().scripts
                if script.metadata and script.metadata.dependencies
            )
        ]

        return cls(
            lifts = tuple(
                chain.from_iterable(
                    concurrently(groups, lambda group: cls.resolved(*group))
                )
            )
        )

    @staticmethod
    def resolved(
        home        : Path,
        requested   : Collection[Requirement],
        constraints : Collection[Requirement] = ()
    ) -> list[Lift]:
        """
        Resolves the newest release of each package `requested` or
        `constraints` names, and names a lift for each pin of either holding
        one exact version that the resolution moves past, dated by that
        release's first upload.
        """
        locked = Pylock.compiled(
            requirement.name for requirement in chain(requested, constraints)
        ).named

        return [
            Lift(
                current  = exact,
                home     = home,
                name     = pin.name,
                newest   = str(newest.version),
                released = newest.released
            )
            for pin in chain(requested, constraints)
            if (exact := Manifest.exact_pin(pin))
            and (newest := locked.get(canonicalize_name(pin.name)))
            and newest.version > Version(exact)
        ]

    def write(self, checkout: Checkout):
        """
        Writes each newest release over the exact pin in the file declaring
        it.
        """
        for lift in self.lifts:
            checkout.respell(
                lift.home,
                rf'("{escape(lift.name)}==){escape(lift.current)}(?=")',
                lift.newest
            )


class SiteLifts(Manager):
    """
    The packages `docs/package.json` pins for the site and the Wrangler
    release `🕹️ Pages` deploys through, read through `bun outdated`, which
    draws a table naming the latest release past each pin, and `bun info`,
    which dates each release and names the dist-tags a prerelease pin
    follows.
    """

    deployer: ClassVar[str] = "wrangler"
    """
    The package the deploy job pins through `deployer_input`.
    """

    deployer_input: ClassVar[str] = "wranglerVersion"
    """
    The input of the deploy step that pins the deployer's release.
    """

    ecosystem: ClassVar[str | None] = "npm"

    folder: ClassVar[Path] = SiteManifest.file.parent
    """
    The folder `bun` runs in, holding the site's manifest and lockfile.
    """

    @classmethod
    def dated(cls, lift: Lift) -> Lift:
        """
        Copies `lift` dated by the time `bun info` lists its newest release
        under.
        """
        return lift.model_copy(
            update = {
                "released": cls.info("time", lift.name, dict[str, datetime]).get(
                    lift.newest
                )
            }
        )

    @classmethod
    def followed(cls, name: str, pin: str) -> str:
        """
        Picks the highest version a dist-tag of the package `name` names at
        or above the prerelease `pin`, or `pin` itself where no tag names a
        version past it.
        """
        floor = Version(pin)

        return max(
            (
                tagged
                for tagged in cls.info("dist-tags", name, dict[str, str]).values()
                if (found := version_of(tagged)) and found >= floor
            ),
            default = pin,
            key     = Version
        )

    @classmethod
    def info[T](cls, field: str, name: str, shape: TypeForm[T]) -> T:
        """
        Reads `field` of the package `name` through `bun info`, as `shape`.
        """
        return parsed(shape, "bun", "info", name, field, "--json", cwd=cls.folder)

    @classmethod
    def read(cls) -> Self:
        """
        Reads each pin of the site's manifest against the `Latest` cell of
        the row `bun outdated` draws for it, a prerelease pin against the
        version `followed` picks instead, and the Wrangler release each
        deploy step pins against the `latest` dist-tag, then dates each pin
        lagging its newest release.
        """
        # Matches a row from the package and its `(dev)` mark to the `Latest` cell.
        latest = {
            row["name"]: row["latest"]
            for row in finditer(
                r"(?m)^\| (?P<name>[@\w]\S*)(?: \(\w+\))? +\| \S+ +\| \S+ +\| "
                r"(?P<latest>\d\S*) +\|$",
                check_output(["bun", "outdated"], cwd=cls.folder, text=True)
            )
        }
        found = chain(
            (
                Lift(
                    current = pin,
                    home    = SiteManifest.file,
                    name    = name,
                    newest  = (
                        cls.followed(name, pin)
                        if Version(pin).is_prerelease
                        else latest.get(name, pin)
                    )
                )
                for name, pin in SiteManifest.read().pins.items()
            ),
            (
                Lift(
                    current = block.node.value,
                    home    = path,
                    name    = cls.deployer,
                    newest  = cls.info(
                        "dist-tags",
                        cls.deployer,
                        dict[str, str]
                    )["latest"]
                )
                for path, step in Workflows.read().steps
                if (block := step.at("with", cls.deployer_input))
            )
        )

        return cls(
            lifts = tuple(
                concurrently(
                    items = (lift for lift in found if lift.newest != lift.current),
                    work  = cls.dated
                )
            )
        )

    def write(self, checkout: Checkout):
        """
        Pins each newest site package in `docs/package.json` and resolves it
        into `docs/bun.lock` through `bun add`, which installs nothing under
        `--lockfile-only`, and writes each newest Wrangler release into the
        deploy step pinning it.
        """
        packages = [
            f"{lift.name}@{lift.newest}"
            for lift in self.lifts
            if lift.home == SiteManifest.file
        ]

        if packages:
            checkout.run(
                "bun",
                "add",
                "--cwd",
                str(self.folder),
                "--dev",
                "--exact",
                "--lockfile-only",
                *packages
            )

        for lift in self.lifts:
            if lift.home != SiteManifest.file:
                checkout.respell(
                    lift.home,
                    checkout.assigned(lift.current, self.deployer_input),
                    lift.newest
                )


class PackageLifts(Manager):
    """
    The packages `uv.lock` resolves, read through `uv lock --upgrade
    --dry-run`, which names each package an upgrade would move, and each
    newest release dated through the lockfile `uv pip compile` writes
    for it. Each `uv lock` runs under `--no-locked`, which overrides the
    `UV_LOCKED` the `[env]` block of `.mise/config.toml` sets.
    """

    ecosystem: ClassVar[str | None] = "pip"

    held: tuple[Lift, ...] = ()
    """
    Each lift `holding` left out, whose package `write` checks `uv.lock` still
    resolves at its current release.
    """

    def check(self, lockfile: Lockfile):
        """
        Compares each package of `held` with `lockfile`, reading its highest
        public version as `highest` does.

        Raises:
            HeldPackageMoved: Where `lockfile` leaves any of them off its
                              current release, with a sentence on each that
                              names each lift depending on the package,
                              since only a lift can be held beside it.
        """
        lifted = {lift.name for lift in self.lifts}
        moved  = []

        for lift in self.held:
            resolved = lockfile.resolved(lift.name)
            release  = resolved[-1].public if resolved else "no release"

            if release != lift.current:
                beside = ", ".join(sorted(lockfile.dependents(lift.name) & lifted))

                moved.append(
                    f"`uv lock` moved {lift.name} from the {lift.current} it is held "
                    f"at to {release}"
                    + (
                        f", so hold each lift depending on it as well: {beside}"
                        if beside
                        else ""
                    )
                )

        if moved:
            raise HeldPackageMoved("\n".join(moved))

    @staticmethod
    def highest(versions: str) -> str:
        """
        Picks the highest public version among `versions`, which the dry run
        lists joined by `, ` where the resolution forks across platforms,
        each opening on `v`.
        """
        return max(map(Version, versions.split(", "))).public

    def holding(self, names: Collection[str]) -> Self:
        """
        Copies the manager with the lift of each package `names` lists moved
        from `lifts` to `held`.
        """
        return super().holding(names).model_copy(
            update = {
                "held": (
                    *self.held,
                    *(lift for lift in self.lifts if lift.name in names)
                )
            }
        )

    @classmethod
    def read(cls) -> Self:
        """
        Reads each `Update` line of the dry run, leaving out each package an
        upgrade only adds or drops, then dates each newest release.
        """
        moved = [
            (line["name"], cls.highest(line["current"]), cls.highest(line["newest"]))
            for line in finditer(
                r"(?m)^Update (?P<name>\S+) (?P<current>v\S+(?:, v\S+)*)"
                r" -> (?P<newest>v\S+(?:, v\S+)*)$",
                run(
                    [
                        "uv", "lock", "--color", "never",
                        "--dry-run", "--no-locked", "--upgrade"
                    ],
                    capture_output = True,
                    check          = True,
                    text           = True
                ).stderr
            )
        ]
        released = Pylock.compiled(
            (f"{name}=={newest}" for name, _, newest in moved),
            "--no-deps"
        ).named if moved else {}

        return cls(
            lifts = tuple(
                Lift(
                    current  = current,
                    home     = Lockfile.file,
                    name     = name,
                    newest   = newest,
                    released = released[canonicalize_name(name)].released
                )
                for name, current, newest in moved
            )
        )

    def write(self, checkout: Checkout):
        """
        Moves each package of `lifts` in `uv.lock` to its newest release.
        The resolver treats every other locked version as a preference, so
        a new release requiring a newer held package moves that package too,
        and the write then puts `uv.lock` back as it stood.

        Raises:
            HeldPackageMoved: Where `uv.lock` leaves a package of `held` off
                              its current release.
        """
        if self.lifts:
            file   = checkout.root / Lockfile.file
            locked = file.read_bytes()

            checkout.run(
                "uv",
                "lock",
                "--no-locked",
                *chain.from_iterable(
                    ("--upgrade-package", lift.name) for lift in self.lifts
                )
            )

            try:
                self.check(Lockfile.read(checkout.root))
            except HeldPackageMoved:
                file.write_bytes(locked)
                raise


def table_text(table: Table) -> str:
    """
    Renders `table` as plain text at whatever width its widest row takes.
    """
    console = Console(
        emoji     = False,
        highlight = False,
        markup    = False,
        width     = 1_000_000
    )

    with console.capture() as captured:
        console.print(table)

    return "\n".join(line.rstrip() for line in captured.get().splitlines())


class ToolLifts(Manager):
    """
    The tools `.mise/config.toml` pins under `[tools]` and the mise
    release it sets as `min_version`, read through `mise outdated --bump`,
    which names the newest release past each pin, and dated through `mise
    ls-remote`. A lift of `uv` moves the `required-version` repeating it,
    and a lift of `python` to another minor moves each `requires-python` and
    the formatter's `target-version`, the homes `repo:audit` holds to them.
    """

    floor: ClassVar[str] = "aqua:jdx/mise"
    """
    The name mise's report gives mise itself, the package the aqua registry
    publishes it under, which the table names `mise`.
    """

    @classmethod
    def lifted(cls, reported: OutdatedTool, tool: str) -> Lift:
        """
        Builds the lift `reported`, mise's entry for `tool`, names, dated by
        the time mise lists the newest release under.
        """
        return Lift(
            current  = reported.requested,
            home     = MiseConfig.file,
            name     = "mise" if tool == cls.floor else tool,
            newest   = reported.bump,
            released = {
                release.version: release.created
                for release in parsed(
                    list[MiseRelease],
                    "mise",
                    "ls-remote",
                    "--json",
                    tool,
                    reported.bump
                )
            }.get(reported.bump)
        )

    @classmethod
    def read(cls) -> Self:
        """
        Reads mise's report of the tools the project config pins, which
        `--local` keeps to the project, then of the floor named at the
        release the config sets, keeping each entry naming a newer release,
        and dates each.
        """
        reported = {
            tool: entry
            for arguments in (
                ["--local"],
                [f"{cls.floor}@{MiseConfig.read().min_version}"]
            )
            for tool, entry in parsed(
                dict[str, OutdatedTool],
                "mise",
                "outdated",
                "--bump",
                "--json",
                *arguments
            ).items()
            if entry.bump
        }

        return cls(
            lifts = tuple(
                concurrently(
                    items = sorted(reported),
                    work  = lambda tool: cls.lifted(reported[tool], tool)
                )
            )
        )

    @staticmethod
    def running() -> Version:
        """
        Reads the version of the mise on the path, the first word `mise
        --version` prints.
        """
        return Version(check_output(["mise", "--version"], text=True).split()[0])

    def write(self, checkout: Checkout):
        """
        Writes each newest release into `.mise/config.toml`, the newest
        mise as `min_version`, the newest `uv` into `required-version` as
        well, and the minor of the newest `python`, where it moves, into
        `requires-python`, `target-version`, and each script's inline
        `requires-python`.
        """
        for lift in self.lifts:
            checkout.respell(
                MiseConfig.file,
                checkout.assigned(
                    lift.current,
                    "min_version" if lift.floor else lift.name
                ),
                lift.newest
            )

            if lift.name == "uv":
                checkout.respell(
                    Manifest.file,
                    checkout.assigned(lift.current, "required-version", "=="),
                    lift.newest
                )

            if lift.interpreter and lift.major:
                before, after = (f"{part.major}.{part.minor}" for part in lift.span)

                for path, key, prefix in (
                    (Manifest.file, "requires-python", ">="),
                    (Manifest.file, "target-version", ""),
                    *(
                        (script.path, "requires-python", ">=")
                        for script in Scripts.read().scripts
                        if script.metadata and script.metadata.requires_python
                    )
                ):
                    checkout.respell(
                        path,
                        checkout.assigned(before, key, prefix),
                        after
                    )


class Attempt(Record):
    """
    One lift tried in a scratch clone, beside the lifts it held back,
    whether `mise ci` passed there, and the log holding what every step
    printed.
    """

    held: tuple[Lift, ...]
    """
    The lifts held back as one, none for the whole lift.
    """

    log: Path
    """
    The log holding what every step printed.
    """

    passed: bool
    """
    Whether every step and `mise ci` passed.
    """

    @property
    def sentence(self) -> str:
        """
        Writes what the attempt found, in a sentence naming its log.
        """
        held = " and ".join(f"{lift.name} at {lift.current}" for lift in self.held)
        lift = f"The lift holding {held}" if held else "The whole lift"

        return (
            f"{lift} {'passes' if self.passed else 'fails'} mise ci, "
            f"as {self.log} records"
        )


class Trial(Record):
    """
    Every attempt one `--try` runs, the whole lift first and then, where it
    fails, the lift holding back each major lift in turn and, where none of
    those passes, each remaining pin in turn.
    """

    attempts: tuple[Attempt, ...]
    """
    Each attempt, in the order it ran.
    """

    @property
    def status(self) -> int:
        """
        Reads the exit status the trial ends on, which is 1 where the whole
        lift fails and 0 otherwise.
        """
        return int(not self.attempts[0].passed)

    @property
    def verdict(self) -> str:
        """
        Names each lift that breaks the tree, meaning `mise ci` fails on the
        whole lift and passes once that lift alone is held back, a paired
        group counting as one lift, or says that no one pin does.
        """
        whole, *held = self.attempts

        if whole.passed:
            return "Every lift not held passes mise ci"

        breaking = [
            " and ".join(f"{lift.name} {lift.newest}" for lift in attempt.held)
            for attempt in held
            if attempt.passed
        ]

        if not breaking:
            return "No one pin held back lets mise ci pass"

        return f"The lift breaking the tree is {', '.join(breaking)}"


class Lifts(Record):
    """
    Every pin the repository carries behind its newest release, gathered
    from each manager's own report, beside the pins `Holds` keeps where
    they stand.
    """

    managers: ClassVar[tuple[type[Manager], ...]] = (
        PackageLifts, RequirementLifts, SiteLifts, ActionLifts, ToolLifts
    )
    """
    Every manager whose pins the task reads, in the order `write` writes
    them. `PackageLifts` writes first, so a held package it finds moved stops
    the write before any other pin moves, and `ToolLifts` writes last, since
    every `uv` command before it runs under the `required-version` it moves.
    """

    found: tuple[Manager, ...]
    """
    Each manager holding its lifts, in the order `managers` names them.
    """

    holds: dict[str, str] = {}
    """
    The reason each held pin stays where it stands, under the pin's name.
    """

    @property
    def groups(self) -> list[tuple[Lift, ...]]:
        """
        Splits the lifts into what a trial holds back as one, which is each
        pin alone but for the pins `SitePins.moving_with` groups. A pin
        named on several rows takes one of them, a major one where it has
        any.
        """
        rows = {lift.name: lift for lift in sorted(self.lifts, key=attrgetter("major"))}

        return [
            tuple(lift for lift in rows.values() if lift.name in group)
            for group in dict.fromkeys(map(SitePins.moving_with, rows))
        ]

    @property
    def lifts(self) -> list[Lift]:
        """
        Lists every lift each manager found, in the managers' order.
        """
        return [lift for manager in self.found for lift in manager.lifts]

    @property
    def table(self) -> Table:
        """
        Draws every lift as one row of a table shaped as Markdown, so the
        table pastes into a pull request as it prints.
        """
        table = Table(
            "Pin",
            "In",
            "Current",
            "Newest",
            "Major",
            "Days",
            "Clears",
            box          = MARKDOWN,
            header_style = None,
            show_edge    = False
        )

        for lift in self.lifts:
            table.add_row(*lift.cells)

        return table

    def attempt(self, held: tuple[Lift, ...], logs: Path) -> Attempt:
        """
        Tries the lift in a scratch clone of the checkout, holding back each
        lift of `held`, then removes the clone.

        Inside the clone, the lift is written and `mise ci` runs, each
        printing into a log under `logs` named for what the attempt
        holds back, which outlives the clone. `mise ci` runs under
        `--continue-on-error`, because `mise run` otherwise exits at the
        first failing row while another row's processes still write into
        the clone as it is removed. A step that fails ends the attempt as
        failed, its error written into the log.
        """
        lifts = self.holding({lift.name for lift in held})
        names = "-".join(lift.name for lift in held).replace("/", "-")
        log   = logs / (f"without-{names}.log" if held else "whole.log")

        logs.mkdir(exist_ok=True, parents=True)

        with TemporaryDirectory(prefix="squirtl-lift.") as scratch, log.open(
            "w",
            encoding = "utf-8"
        ) as output:
            clone = Checkout(root=Path.cwd()).cloned(Path(scratch) / "clone", output)

            try:
                lifts.write(clone)
                clone.run("mise", "run", "--continue-on-error", "repo:ci")
            except (CalledProcessError, ValueError) as error:
                print(error, file=output)
                passed = False
            else:
                passed = True

        return Attempt(held=held, log=log, passed=passed)

    def holding(self, names: Collection[str]) -> Self:
        """
        Copies the lifts with the lift of each pin `names` lists left out,
        so the pin stays where it stands.
        """
        return self.model_copy(
            update = {"found": tuple(manager.holding(names) for manager in self.found)}
        )

    def lift(self, *, held: Iterable[str], trying: bool, writing: bool) -> int:
        """
        Prints the table of every lift and each held pin beside its reason,
        then tries the lift, writes it, or both where a lift remains. Each
        held pin stays where it stands, the write stopping with every file
        as it stood where `uv lock` would move a held package, and the write
        runs only after a passing trial where both are asked for.

        A pin is held where `held` or `Holds` names it, where `refused`
        names it, or where it moves with a held pin, since a partner left
        moving fails `repo:audit`.

        Returns:
            The exit status, which is 2 where a hold names a pin the table
            does not list, before any trial or write, 1 where the trial
            fails or the write stops on a held package, and 0 otherwise.
        """
        named = (
            self.refused()
            | dict.fromkeys(held, "`--hold` names it for this run")
            | self.holds
        )
        holds = {
            lift.name: f"it moves with {name}"
            for name in named
            for lift in self.lifts
            if lift.name in SitePins.moving_with(name)
        } | named

        if self.lifts:
            print(table_text(self.table), flush=True)
        else:
            print("Every pin stands at its newest release")

        for lift in self.lifts:
            if lift.name in holds:
                print(
                    f"Leaving {lift.name} at {lift.current}, "
                    f"because {holds[lift.name]}",
                    flush = True
                )

        if unknown := sorted(holds.keys() - {lift.name for lift in self.lifts}):
            Console(stderr=True).out(
                f"The table lists no pin named {', '.join(unknown)} to hold, so the "
                "lift stops before any trial or write",
                highlight = False
            )
            return 2

        lifts = self.holding(holds.keys())

        if not lifts.lifts:
            return 0

        if trying:
            trial = lifts.tried(Path(".cache/lift"))
            print(trial.verdict, flush=True)

            if trial.status:
                return trial.status

        if writing:
            try:
                lifts.write(Checkout(root=Path.cwd()))
            except HeldPackageMoved as error:
                Console(stderr=True).out(
                    f"{error}\nThe write stops with every file as it stood",
                    highlight = False
                )
                return 1

        return 0

    @classmethod
    def read(cls) -> Self:
        """
        Reads every manager's report at once, since each waits on a
        registry, marks the open Dependabot alerts each lift clears, and
        reads the holds `Holds` declares.
        """
        alerts = Alert.listed()

        return cls(
            found = tuple(
                manager.clearing(alerts)
                for manager in concurrently(cls.managers, methodcaller("read"))
            ),
            holds = Holds.read().reasons
        )

    def refused(self) -> dict[str, str]:
        """
        Reads the reason the lift of mise itself stays out of this run,
        where the mise on the path is older than the newest release, since
        mise exits on a `min_version` above its own version, which would
        fail every command of a trial and a write.
        """
        return {
            lift.name: (
                f"the running mise {running} refuses a `min_version` of "
                f"{lift.newest} until `mise self-update` moves it"
            )
            for lift in self.lifts
            if lift.floor and (running := ToolLifts.running()) < Version(lift.newest)
        }

    def tried(self, logs: Path) -> Trial:
        """
        Tries the whole lift in a scratch clone and, where `mise ci` fails
        there, tries it again holding back each major lift in turn and,
        where none of those passes, each remaining pin in turn, printing
        each attempt's sentence as it ends, since each runs for minutes.
        Each of `groups` is held back as one, and it counts as major where
        any of its lifts is.
        """
        attempts = []
        groups   = self.groups
        majors   = [group for group in groups if any(lift.major for lift in group)]

        for stage in ([()], majors, [group for group in groups if group not in majors]):
            for held in stage:
                attempts.append(self.attempt(held, logs))
                print(attempts[-1].sentence, flush=True)

            if any(attempt.passed for attempt in attempts):
                break

        return Trial(attempts=tuple(attempts))

    def write(self, checkout: Checkout):
        """
        Writes every lift into `checkout` in the managers' order, then locks
        and installs the tools the lift pins and re-resolves every lockfile
        through `lock:sync`, building `.venv` again on the interpreter the
        lift pins where `python` moves, since `uv sync` alone keeps `.venv`
        on the interpreter it was built on while that interpreter satisfies
        `requires-python`, as a move within the minor leaves it.
        """
        for manager in self.found:
            manager.write(checkout)

        for command in (
            ("mise", "lock"),
            ("mise", "install"),
            ("mise", "run", "lock:sync"),
            *(
                (
                    ("mise", "x", "--", "uv", "venv", "--clear"),
                    ("mise", "x", "--", "uv", "sync")
                )
                if any(lift.interpreter for lift in self.lifts)
                else ()
            )
        ):
            checkout.run(*command)
