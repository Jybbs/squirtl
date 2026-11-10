"""
Pins the records a release carries its trained runs through, covering:

- The tar each run packs into, holding its record on the default cartridge
  and its demonstration under `data/runs/`, its episodes, and a checkpoint
  of its weights alone, the same bytes on a second pack, and a run missing
  its checkpoint or its episodes, which it refuses by name
- The manifest beside the tars, holding the demonstration apart from the
  trained runs and refusing a recommended run it does not list
- The release read from GitHub's REST API, its manifest, and the runs it
  fetches, checked against both digests and unpacked whole or not at all
- The runs a selector matches, and the runs `RunSelection` reads from a
  directory or a release, with the default selection of each command
"""

from collections.abc   import Callable
from common.releases   import ADDRESS, GitHub
from email.message     import Message
from hashlib           import sha256
from io                import BytesIO
from json              import dumps, loads
from pathlib           import Path
from pydantic          import ValidationError
from pytest            import MonkeyPatch, mark, param, raises
from releases.conftest import Recorder
from tarfile           import open as open_tar
from urllib.error      import HTTPError
from zipfile           import ZipFile

from squirtl.agent.checkpoint import Weights
from squirtl.agent.schemas    import Algorithm
from squirtl.releases.schemas import GithubRelease, PackedRun, ReleaseManifest, ReleaseSettings, RunSelection, Selector
from squirtl.runs.schemas     import Run, Start


def test_a_directory_selection_reads_each_directory_alone(committed: list[Run]):
    """
    Asserts that a selection of run directories reads each in order, and
    `one` the first, without reading any release.
    """
    selection = RunSelection(
        directories = (committed[2].directory, committed[0].directory)
    )

    assert [run.name for run in selection.every()] == [
        committed[2].name,
        committed[0].name
    ]
    assert selection.one().name == committed[2].name


def test_a_fetch_unpacks_the_run_as_it_was_packed(
    committed : list[Run],
    published : GitHub,
    tmp_path  : Path
):
    """
    Asserts that fetching a run into an empty folder unpacks its record, its
    episodes, and its weights, leaving nothing else in the folder, and that
    a second fetch downloads nothing.
    """
    release = GithubRelease.read()
    run     = release.fetch(release.manifest.recommended, tmp_path / "runs")

    assert (
        run.name, run.directory
    ) == (committed[0].name, tmp_path / "runs" / run.name)
    assert sorted(path.name for path in run.directory.iterdir()) == [
        "checkpoint.npz", "episodes.jsonl", "run.json"
    ]
    assert run.episodes.read_bytes() == committed[0].episodes.read_bytes()
    assert [path.name for path in (tmp_path / "runs").iterdir()] == [run.name]

    published.served.clear()

    assert release.fetch(release.manifest.recommended, tmp_path / "runs") == run


def test_a_recommended_run_the_manifest_does_not_list_is_refused(committed: list[Run]):
    """
    Asserts that packing under a `recommended_run` naming the demonstration
    rather than a trained run raises a `ValidationError` naming it.
    """
    with raises(ValidationError, match=committed[3].name):
        ReleaseManifest.pack(ReleaseSettings(recommended_run=committed[3].name))


@mark.parametrize(
    "missing",
    [
        param(lambda run: run.checkpoint, id="the-checkpoint"),
        param(lambda run: run.episodes,   id="the-episodes")
    ]
)
def test_a_run_missing_its_checkpoint_or_its_episodes_is_refused_by_name(
    missing  : Callable[[Run], Path],
    recorded : Recorder,
    tmp_path : Path
):
    """
    Asserts that packing a run whose checkpoint or episodes are gone raises
    `FileNotFoundError` naming the run's directory and the file it lacks.
    """
    run = recorded(1)
    missing(run).unlink()

    with raises(
        FileNotFoundError,
        match = f"{run.directory} holds no {missing(run).name}"
    ):
        PackedRun.pack(tmp_path, run)


def test_a_release_attaching_no_manifest_is_refused_by_its_tag():
    """
    Asserts that reading the manifest of a release attaching none raises
    `ValueError` naming the release's tag and the manifest's file.
    """
    release = GithubRelease(published_at="2026-11-10T00:00:00Z", tag_name="0.1.0")

    with raises(ValueError, match="The release 0.1.0 attaches no manifest.json"):
        _ = release.manifest


@mark.parametrize(
    ("tag", "address"),
    [
        param(None,    f"{ADDRESS}/latest",      id="the-latest"),
        param("0.2.0", f"{ADDRESS}/tags/0.2.0", id="a-tag")
    ]
)
def test_a_release_reads_from_the_address_its_tag_gives(
    address   : str,
    published : GitHub,
    tag       : str | None
):
    """
    Asserts that reading a release asks the REST API's address for the tag,
    or for the latest release without one, under the User-Agent `squirtl`.
    """
    published.served[address] = dumps(
        {"published_at": "2026-11-10T00:00:00Z", "tag_name": "read"}
    ).encode()

    assert GithubRelease.read(tag).tag == "read"
    assert published.agents == ["squirtl"]


@mark.parametrize(
    ("tag", "message"),
    [
        param("9.9.9", "Jybbs/squirtl publishes no release 9.9.9$", id="a-tag"),
        param(None,    "Jybbs/squirtl publishes no release$",       id="the-latest")
    ]
)
def test_a_release_github_does_not_publish_is_refused(
    github  : GitHub,
    message : str,
    tag     : str | None
):
    """
    Asserts that reading a release GitHub answers with 404 raises
    `ValueError` naming the repository, and the tag where one is given.
    """
    with raises(ValueError, match=message):
        GithubRelease.read(tag)


def test_a_second_pack_writes_the_same_bytes(packed: ReleaseManifest):
    """
    Asserts that packing the same runs again writes each tar and the
    manifest byte for byte as the first pack did.
    """
    first = {path: path.read_bytes() for path in packed.files}
    ReleaseManifest.pack(ReleaseSettings(recommended_run=packed.recommended_run))

    assert {path: path.read_bytes() for path in packed.files} == first


def test_a_selection_matching_no_run_is_refused_by_the_tag(published: GitHub):
    """
    Asserts that a selector matching none of a release's runs raises
    `ValueError` naming the release's tag.
    """
    with raises(ValueError, match="No run of the release 0.2.0 matches"):
        RunSelection(release="0.2.0", selector=Selector(seed=5)).every()


def test_a_tar_holds_the_record_the_episodes_and_the_weights_alone(
    committed : list[Run],
    packed    : ReleaseManifest
):
    """
    Asserts that the tar of a run following a demonstration holds its
    folder's record, naming the default cartridge and the demonstration
    under `data/runs/`, its episodes as written, and a checkpoint holding
    `agent.pt` alone, whose weights read back as the run's.
    """
    run = committed[1]

    with open_tar(ReleaseManifest.folder / packed.runs[1].asset, "r:zst") as archive:
        members = {
            Path(name).name: archive.extractfile(name).read()
            for name in archive.getnames()
            if name.startswith(f"{run.name}/")
        }

    record = loads(members["run.json"])["settings"]
    (ReleaseManifest.folder / "checkpoint.npz").write_bytes(members["checkpoint.npz"])

    assert sorted(members) == ["checkpoint.npz", "episodes.jsonl", "run.json"]
    assert (record["emulator"]["cartridge"], record["curriculum"]["demonstration"]) == (
        "data/rom.gb",
        f"data/runs/{committed[3].name}"
    )
    assert members["episodes.jsonl"] == run.episodes.read_bytes()
    assert ZipFile(ReleaseManifest.folder / "checkpoint.npz").namelist() == ["agent.pt"]
    assert [
        (weights.online["weight"].tolist(), weights.step)
        for weights in map(
            Weights.from_path,
            (ReleaseManifest.folder / "checkpoint.npz", run.checkpoint)
        )
    ] == [([1.0, 2.0], 8)] * 2


@mark.parametrize(
    ("asset_digest", "manifest_digest"),
    [
        param("sha256:0", None, id="the-assets-digest"),
        param(None,       "0",  id="the-manifests-digest")
    ]
)
def test_a_tar_differing_from_either_digest_is_refused_leaving_no_run(
    asset_digest    : str | None,
    manifest_digest : str | None,
    published       : GitHub,
    tmp_path        : Path
):
    """
    Asserts that a tar whose digest differs from the one its asset carries,
    or, where GitHub carries none, from the one the manifest records, is
    refused naming the run, leaving nothing in the folder.
    """
    release = GithubRelease.read()
    listing = release.manifest.recommended
    damaged = release.model_copy(
        update = {
            "assets": tuple(
                asset.model_copy(update={"digest": asset_digest})
                if asset.name == listing.asset else asset
                for asset in release.assets
            )
        }
    )

    with raises(ValueError, match=listing.name):
        damaged.fetch(
            listing.model_copy(update={"sha256": manifest_digest or listing.sha256}),
            tmp_path / "runs"
        )

    assert list((tmp_path / "runs").iterdir()) == []


def test_a_tar_reaching_outside_its_folder_is_refused(
    published : GitHub,
    tmp_path  : Path
):
    """
    Asserts that a tar holding a member whose path leaves the folder
    it unpacks into, which `tarfile`'s `data` filter refuses, raises
    `ValueError`, leaving no directory behind.
    """
    release = GithubRelease.read()
    listing = release.manifest.recommended
    escape  = tmp_path / "escape.tar.zst"

    with open_tar(escape, "w:zst") as archive:
        archive.add(Run.folder / listing.name / "run.json", "../outside.json")

    asset = release.attached(listing.asset)
    published.served[asset.url] = escape.read_bytes()
    digest  = sha256(published.served[asset.url]).hexdigest()
    escaped = release.model_copy(
        update = {
            "assets": tuple(
                attached.model_copy(update={"digest": f"sha256:{digest}"})
                if attached is asset else attached
                for attached in release.assets
            )
        }
    )

    with raises(ValueError, match="does not unpack"):
        escaped.fetch(listing.model_copy(update={"sha256": digest}), tmp_path / "runs")

    assert list((tmp_path / "runs").iterdir()) == []


@mark.parametrize(
    ("selector", "matched"),
    [
        param(Selector(),                          [0, 1, 2], id="nothing-set"),
        param(Selector(agent=Algorithm.PPO),       [0, 1],    id="the-agent"),
        param(Selector(start=Start.CURRICULUM),    [1],       id="the-start"),
        param(Selector(agent="ppo", seed=2),       [],        id="no-run")
    ]
)
def test_a_selector_matches_each_run_holding_every_setting_it_sets(
    matched  : list[int],
    packed   : ReleaseManifest,
    selector : Selector
):
    """
    Asserts that a selector matches the trained runs holding every setting
    it sets, and every run where it sets none.
    """
    assert [run for run in packed.runs if selector.matches(run)] == [
        packed.runs[index] for index in matched
    ]


@mark.parametrize(
    "fields",
    [
        param({},                                            id="neither"),
        param({"directories": (Path("x"),), "release": "0.2.0"}, id="both"),
        param(
            {"directories": (Path("x"),), "selector": Selector(seed=1)},
            id = "a-selector-beside-a-directory"
        )
    ]
)
def test_a_selection_names_a_directory_or_a_release_alone(fields: dict[str, object]):
    """
    Asserts that a selection naming neither source, both, or a selector
    beside run directories is refused.
    """
    with raises(ValidationError):
        RunSelection(**fields)


@mark.parametrize(
    ("selector", "every", "one"),
    [
        param(None,                  [0, 3],    0,    id="the-default"),
        param(Selector(seed=2),      [2],       2,    id="one-match"),
        param(Selector(agent="ppo"), [0, 1, 3], None, id="three-matches")
    ]
)
def test_a_release_selection_reads_the_runs_each_command_plays(
    committed : list[Run],
    every     : list[int],
    github    : GitHub,
    one       : int | None,
    recorded  : Recorder,
    selector  : Selector | None
):
    """
    Asserts that `every` reads each seed of the recommended run's agent
    and start with no selector and every match otherwise, and that `one`
    reads the recommended run with no selector and the selector's one match
    otherwise, refusing several matches by naming each, every run fetched
    into `Run.folder` once the runs packed there are moved away.
    """
    trained = [*committed[:3], recorded(4, seed=3)]
    github.publish(
        ReleaseManifest.pack(ReleaseSettings(recommended_run=trained[0].name))
    )
    Run.folder.rename("data/packed")
    selection = RunSelection(release="0.2.0", selector=selector)

    assert [(run.name, run.directory) for run in selection.every()] == [
        (trained[index].name, Run.folder / trained[index].name) for index in every
    ]

    if one is None:
        with raises(
            ValueError,
            match = ", ".join(trained[index].name for index in every)
        ):
            selection.one()
    else:
        assert selection.one().name == trained[one].name


def test_another_error_from_github_is_raised_as_it_came(monkeypatch: MonkeyPatch):
    """
    Asserts that an error GitHub answers with other than 404 reaches the
    caller as the `HTTPError` it raised.
    """

    def refused(request: object):
        """
        Answers every request with GitHub's 403.
        """
        raise HTTPError(ADDRESS, 403, "Forbidden", Message(), BytesIO())

    monkeypatch.setattr("squirtl.releases.schemas.urlopen", refused)

    with raises(HTTPError):
        GithubRelease.read()


def test_the_manifest_lists_the_demonstration_apart_with_each_digest(
    committed : list[Run],
    packed    : ReleaseManifest
):
    """
    Asserts that the manifest lists the three trained runs and, apart from
    them, the demonstration, each beside the settings it recorded and the
    digest of its tar, and reads back from `manifest.json` as written.
    """
    assert [(run.name, run.agent, run.start, run.seed) for run in packed.runs] == [
        (committed[0].name, Algorithm.PPO, Start.BEDROOM,    1),
        (committed[1].name, Algorithm.PPO, Start.CURRICULUM, 1),
        (committed[2].name, Algorithm.DQN, Start.BEDROOM,    2)
    ]
    assert [run.name for run in packed.demonstrations] == [committed[3].name]
    assert all(
        sha256(
            (ReleaseManifest.folder / run.asset).read_bytes()
        ).hexdigest() == run.sha256
        for run in packed.packed
    )
    assert ReleaseManifest.model_validate_json(
        (ReleaseManifest.folder / ReleaseManifest.file).read_bytes()
    ) == packed
