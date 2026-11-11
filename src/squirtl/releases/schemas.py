"""
Defines the records a release of SquiRtL carries its trained runs through:

- `PackedRun`, one run `squirtl pack` writes as a Zstandard tar, and
  `ReleaseManifest`, the listing of every such tar under the
  `ReleaseSettings` the pack read
- `GithubRelease` and `GithubAsset`, a release GitHub publishes and each
  file attached to it, from which `squirtl fetch` unpacks the runs
- `Selector` and `RunSelection`, the runs `squirtl watch` and `squirtl
  evaluate` read from a run directory or from a release
"""

from collections.abc    import Container
from functools          import cached_property
from hashlib            import file_digest
from http               import HTTPStatus
from importlib.metadata import metadata
from pathlib            import Path
from pydantic           import AwareDatetime, Field, NonNegativeInt, model_validator
from rich.console       import Console
from rich.progress      import wrap_file
from shutil             import copyfileobj
from tarfile            import TarError, TarInfo, open as open_tar
from tempfile           import TemporaryDirectory
from typing             import ClassVar, Self
from urllib.error       import HTTPError
from urllib.parse       import urlparse
from urllib.request     import Request, urlopen

from squirtl.agent.checkpoint import Weights
from squirtl.agent.schemas    import Algorithm
from squirtl.docs.results     import Results
from squirtl.emulator.schemas import EmulatorSettings, Record
from squirtl.runs.schemas     import Run, RunListing, Start


def requested(url: str) -> Request:
    """
    Builds a request for `url` carrying the User-Agent GitHub's REST API
    requires of every call and the media type its documentation recommends.
    """
    return Request(
        url,
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "squirtl"}
    )


class GithubAsset(Record, extra="ignore"):
    """
    One file a GitHub release attaches, under the fields GitHub's REST API
    names.
    """

    name: str
    """
    The file's name.
    """

    size: NonNegativeInt
    """
    The file's length in bytes.
    """

    digest: str | None = None
    """
    The digest GitHub computed for the file, as `sha256:<hex>`, or `None`
    for a file it carries none for.
    """

    url: str = Field(alias="browser_download_url")
    """
    The address the file downloads from with no login.
    """

    def download(self, path: Path) -> str:
        """
        Writes the file to `path` behind a progress bar on standard error
        bearing its name.

        Returns:
            The SHA-256 digest of what was written, in hexadecimal.
        """
        with (
            urlopen(requested(self.url)) as response,
            wrap_file(
                response,
                self.size,
                console     = Console(stderr=True),
                description = self.name
            ) as source,
            path.open("wb") as file
        ):
            copyfileobj(source, file)

        with path.open("rb") as file:
            return file_digest(file, "sha256").hexdigest()


def normalized(entry: TarInfo) -> TarInfo:
    """
    Clears the owner and the time of a tar's `entry` and sets its mode, so
    the same file always writes the same header.
    """
    return entry.replace(
        deep  = False,
        gid   = 0,
        gname = "",
        mode  = 0o644,
        mtime = 0,
        uid   = 0,
        uname = ""
    )


class PackedRun(RunListing):
    """
    One run as `squirtl pack` writes it, a Zstandard tar holding its
    `run.json`, its episodes, and a checkpoint of its `Weights` alone, all
    inside a folder bearing its name.
    """

    suffix: ClassVar[str] = ".tar.zst"

    sha256: str
    """
    The SHA-256 digest of the tar, in hexadecimal.
    """

    @property
    def asset(self) -> str:
        """
        Names the tar's file, the name of the asset a release attaches it
        under.
        """
        return self.name + self.suffix

    @classmethod
    def pack(cls, folder: Path, run: Run) -> Self:
        """
        Writes `run` into `folder` as the tar `asset` names, its record
        naming the cartridge `EmulatorSettings` defaults to and any
        demonstration by its name under `Run.folder`, and its checkpoint
        holding the agent's `Weights` with no optimizer state and no replay
        memory. Each member's header is `normalized`, so a run whose files
        are unchanged writes the same bytes.
        """
        curriculum, emulator = run.settings.curriculum, run.settings.emulator
        demonstration        = curriculum.demonstration
        settings             = run.settings.model_copy(
            update = {
                "curriculum" : curriculum.model_copy(
                    update = {
                        "demonstration":
                            demonstration and Run.folder / demonstration.name
                    }
                ),
                "emulator"   : emulator.model_copy(
                    update = {"cartridge": EmulatorSettings().cartridge}
                )
            }
        )
        tar = folder / (run.name + cls.suffix)

        with TemporaryDirectory() as staging:
            record     = Path(staging, "run.json")
            checkpoint = Path(staging, "checkpoint.npz")
            record.write_text(
                run.model_copy(update={"settings": settings}).model_dump_json(indent=2),
                encoding = "utf-8"
            )
            Weights.from_path(run.checkpoint).save(checkpoint)

            with open_tar(tar, "w:zst") as archive:
                for path in (record, checkpoint, run.episodes):
                    archive.add(path, f"{run.name}/{path.name}", filter=normalized)

        with tar.open("rb") as file:
            return cls.of(run, sha256=file_digest(file, "sha256").hexdigest())


class ReleaseSettings(Record):
    """
    The settings `squirtl pack` writes a release's runs under.
    """

    recommended_run: str = "20261111T020527.724383Z"
    """
    The name of the run a release plays where no selection names one.
    """

    def check_recommends(self, names: Container[str]):
        """
        Refuses a `recommended_run` naming none of `names`, the names of the
        trained runs.

        Raises:
            ValueError: Where none bears that name.
        """
        if self.recommended_run not in names:
            raise ValueError(
                f"The recommended run {self.recommended_run} is no trained run"
            )


class ReleaseManifest(ReleaseSettings):
    """
    The listing of every tar a release carries, written as `file`
    beside them, the trained runs `docs/runs/` commits apart from each
    demonstration their curriculum follows, so no selection of the trained
    runs matches a demonstration.
    """

    file   : ClassVar[str]  = "manifest.json"
    folder : ClassVar[Path] = Path("dist/runs")

    demonstrations: tuple[PackedRun, ...]
    """
    Each demonstration a trained run follows, in the order of its name.
    """

    runs: tuple[PackedRun, ...]
    """
    Each trained run, in the order of its name.
    """

    @property
    def files(self) -> tuple[Path, ...]:
        """
        Locates each tar the manifest lists and then the manifest itself,
        each under `folder`.
        """
        return (
            *(self.folder / run.asset for run in self.packed),
            self.folder / self.file
        )

    @property
    def packed(self) -> tuple[PackedRun, ...]:
        """
        Lists every run a tar holds, the trained runs and then each
        demonstration.
        """
        return self.runs + self.demonstrations

    @property
    def recommended(self) -> PackedRun:
        """
        Finds the trained run `recommended_run` names.
        """
        return next(run for run in self.runs if run.name == self.recommended_run)

    @classmethod
    def pack(cls, settings: ReleaseSettings) -> Self:
        """
        Packs each run `Results.folder` lists, then each demonstration
        those runs follow, from its directory under `Run.folder` by its
        name, into `folder`, and writes the manifest listing them there
        as `file`. Before writing any tar, it checks the recommended run
        through `ReleaseSettings.check_recommends`, then each run's files
        through `Run.check_files` and every line of its episodes through
        `Run.check_episodes`.

        Raises:
            FileNotFoundError : Where a run's directory holds no record, no
                                checkpoint, or no episodes.
            ValueError        : Where `settings` recommends none of the
                                trained runs, or a line of a run's episodes
                                holds no `Episode`.
        """
        trained = [
            Run.read(Run.folder / directory.name)
            for directory in sorted(Results.folder.iterdir())
        ]
        settings.check_recommends({run.name for run in trained})
        followed = sorted(
            {
                demonstration.name
                for run in trained
                if (demonstration := run.settings.curriculum.demonstration)
            }
        )
        demonstrations = [Run.read(Run.folder / name) for name in followed]

        for run in (*trained, *demonstrations):
            run.check_files()
            run.check_episodes()

        cls.folder.mkdir(exist_ok=True, parents=True)

        manifest = cls(
            **dict(settings),
            demonstrations = tuple(
                PackedRun.pack(cls.folder, run) for run in demonstrations
            ),
            runs = tuple(PackedRun.pack(cls.folder, run) for run in trained)
        )
        (cls.folder / cls.file).write_text(
            manifest.model_dump_json(indent=2),
            encoding = "utf-8"
        )

        return manifest

    @model_validator(mode="after")
    def recommends_a_run(self) -> Self:
        """
        Refuses a `recommended_run` naming none of the trained runs.

        Raises:
            ValueError: Where no trained run bears that name.
        """
        self.check_recommends({run.name for run in self.runs})

        return self


class GithubRelease(Record, extra="ignore"):
    """
    One release a GitHub repository publishes, under the fields GitHub's
    REST API names.
    """

    assets: tuple[GithubAsset, ...] = ()
    """
    Each file the release attaches.
    """

    published: AwareDatetime = Field(alias="published_at")
    """
    When the release was published.
    """

    tag: str = Field(alias="tag_name")
    """
    The tag the release names.
    """

    @cached_property
    def manifest(self) -> ReleaseManifest:
        """
        Downloads the manifest the release attaches.

        Raises:
            ValueError: Where the release attaches no manifest.
        """
        with urlopen(requested(self.attached(ReleaseManifest.file).url)) as response:
            return ReleaseManifest.model_validate_json(response.read())

    def attached(self, name: str) -> GithubAsset:
        """
        Finds the file the release attaches under `name`.

        Raises:
            ValueError: Where it attaches none, naming the release's tag.
        """
        if asset := next((asset for asset in self.assets if asset.name == name), None):
            return asset

        raise ValueError(f"The release {self.tag} attaches no {name}")

    def fetch(self, run: PackedRun, folder: Path = Run.folder) -> Run:
        """
        Downloads the tar of `run` through its asset's `download`, checks
        it against the digest its asset carries and the one the manifest
        records, and unpacks it through `tarfile`'s `data` filter into a
        temporary directory inside `folder`, which then takes the run's name
        there. A run `folder` already holds downloads nothing.

        Returns:
            The run, read from its directory inside `folder`.

        Raises:
            ValueError: Where the release attaches no tar for the run,
                        the tar's digest differs from either, or `tarfile`
                        refuses to unpack the tar.
        """
        directory = folder / run.name

        if not directory.exists():
            asset = self.attached(run.asset)
            folder.mkdir(exist_ok=True, parents=True)

            with TemporaryDirectory(dir=folder, prefix=".") as staging:
                tar    = Path(staging, asset.name)
                digest = asset.download(tar)

                if (
                    digest              != run.sha256
                    or asset.digest not in {None, f"sha256:{digest}"}
                ):
                    raise ValueError(
                        f"The tar of {run.name} in the release {self.tag} has the "
                        f"SHA-256 digest {digest}, where its asset carries "
                        f"{asset.digest} and the manifest records {run.sha256}"
                    )

                try:
                    with open_tar(tar, "r:zst") as archive:
                        archive.extractall(staging, filter="data")
                except TarError as error:
                    raise ValueError(
                        f"The tar of {run.name} in the release {self.tag} does not "
                        f"unpack, since {error}"
                    ) from error

                Path(staging, run.name).rename(directory)

        return Run.read(directory)

    def matched(self, selector: Selector | None) -> tuple[PackedRun, ...]:
        """
        Lists the trained runs the release's manifest lists that `selector`
        matches, or every run a tar holds where `selector` is `None`.

        Raises:
            ValueError: Where none does, naming the release's tag.
        """
        if selector is None:
            return self.manifest.packed

        if matches := tuple(filter(selector.matches, self.manifest.runs)):
            return matches

        raise ValueError(f"No run of the release {self.tag} matches the selection")

    @classmethod
    def read(cls, tag: str | None = None) -> Self:
        """
        Reads the release of SquiRtL's repository that `tag` names, or
        its latest release where `tag` is `None`, over GitHub's REST API
        with no login, the repository being the one the package metadata's
        `Repository` address names.

        Raises:
            HTTPError  : Where GitHub answers with an error other than 404.
            ValueError : Where GitHub publishes no such release.
        """
        addresses = dict(
            entry.split(", ") for entry in metadata("squirtl").get_all("Project-URL")
        )
        repository = urlparse(addresses["Repository"]).path
        release    = f"tags/{tag}" if tag else "latest"

        try:
            with urlopen(
                requested(
                    url = f"https://api.github.com/repos{repository}/releases/{release}"
                )
            ) as response:
                return cls.model_validate_json(response.read())
        except HTTPError as error:
            error.close()

            if error.code != HTTPStatus.NOT_FOUND:
                raise

            raise ValueError(
                f"{repository.strip('/')} publishes no release {tag or ''}".rstrip()
            ) from error


class Selector(Record):
    """
    The settings selecting among a release's trained runs, each one left
    unset matching every run.
    """

    agent: Algorithm | None = None
    """
    The agent the run trained.
    """

    seed: NonNegativeInt | None = None
    """
    The seed the run's random draws derive from.
    """

    start: Start | None = None
    """
    Where the run's training episodes start.
    """

    def matches(self, run: RunListing) -> bool:
        """
        Decides whether `run` holds every setting the selector sets.
        """
        return all(value in {None, getattr(run, name)} for name, value in self)


class RunSelection(Record):
    """
    The runs a command reads, from the run directories it names or from the
    runs of the release it names that its selector matches, fetching each
    run `Run.folder` does not hold.
    """

    directories: tuple[Path, ...] = ()
    """
    The directory of each run.
    """

    release: str | None = None
    """
    The tag of the release to read the runs from.
    """

    selector: Selector | None = None
    """
    The settings selecting among the release's runs, or `None` for the
    default selection.
    """

    @cached_property
    def published(self) -> GithubRelease:
        """
        Reads the release `release` names, or the latest one where it is
        `None`.
        """
        return GithubRelease.read(self.release)

    def every(self) -> tuple[Run, ...]:
        """
        Reads every run the selection names, its selector's matches, or,
        with no selector, every run of the recommended run's agent and
        start.

        Raises:
            ValueError: Where no run of the release matches.
        """
        if self.directories:
            return tuple(map(Run.read, self.directories))

        release     = self.published
        recommended = release.manifest.recommended

        return tuple(
            release.fetch(run)
            for run in release.matched(
                self.selector or Selector(
                    agent = recommended.agent,
                    start = recommended.start
                )
            )
        )

    def one(self) -> Run:
        """
        Reads the one run the selection names, its directory, its selector's
        one match, or, with no selector, the recommended run.

        Raises:
            ValueError: Where no run of the release matches, or more than
                        one does, naming each.
        """
        if self.directories:
            return Run.read(self.directories[0])

        release = self.published

        if self.selector is None:
            return release.fetch(release.manifest.recommended)

        match release.matched(self.selector):
            case (run,): return release.fetch(run)
            case runs:
                raise ValueError(
                    f"The selection matches more than one run of the release "
                    f"{release.tag}: {', '.join(run.name for run in runs)}"
                )

    @model_validator(mode="after")
    def sourced(self) -> Self:
        """
        Refuses a selection naming both run directories and a release, or
        neither, and a selector beside run directories.

        Raises:
            ValueError: Where it names both or neither, or a selector
                        without a release.
        """
        if bool(self.directories) == (self.release is not None):
            raise ValueError("Name either a run directory or --release, and not both")

        if self.selector is not None and self.release is None:
            raise ValueError(
                "--agent, --start, and --seed select among a release's runs"
            )

        return self
