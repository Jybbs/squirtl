"""
Pins what `squirtl pack` does, covering:

- The folder it prints and the manifest it writes there, recommending the
  run `--recommended-run` names
- A run missing its checkpoint, a recommended run no tar holds, and a run
  with a line holding no episode, each exiting 1
"""

from common.cli import Invoker
from pathlib    import Path

from squirtl.releases.schemas import ReleaseManifest


def test_a_pack_prints_its_folder_and_lists_the_recommended_run(
    invoke  : Invoker,
    trained : Path
):
    """
    Asserts that packing a committed run exits zero, printing `dist/runs`,
    where the manifest lists the run as the one `--recommended-run` names.
    """
    Path("docs/runs", trained.name).mkdir(parents=True)
    invocation = invoke(["pack", "--recommended-run", trained.name])
    manifest   = ReleaseManifest.model_validate_json(
        (ReleaseManifest.folder / ReleaseManifest.file).read_bytes()
    )

    assert (invocation.code, invocation.output.strip()) == (0, "dist/runs")
    assert manifest.recommended.name == trained.name


def test_a_run_missing_its_checkpoint_or_the_recommended_run_exits_1(
    invoke  : Invoker,
    trained : Path
):
    """
    Asserts that packing under the default recommended run, which no tar
    holds, and packing a run whose checkpoint is gone each exit 1, logging
    the reason.
    """
    Path("docs/runs", trained.name).mkdir(parents=True)
    recommended = invoke(["pack"])
    (trained / "checkpoint.npz").unlink()
    missing = invoke(["pack", "--recommended-run", trained.name])

    assert (recommended.code, "is no trained run" in recommended.log) == (1, True)
    assert (
        missing.code,
        f"{trained} holds no checkpoint.npz" in missing.log
    ) == (1, True)


def test_a_run_with_a_line_holding_no_episode_exits_1_naming_the_line(
    invoke  : Invoker,
    trained : Path
):
    """
    Asserts that packing a run whose first episode records a share under a
    name since retired exits 1, logging the line of its episodes, and writes
    no tar.
    """
    Path("docs/runs", trained.name).mkdir(parents=True)
    episodes = trained / "episodes.jsonl"
    episodes.write_text(
        episodes.read_text(encoding="utf-8").replace('"goal"', '"starter"', 1),
        encoding = "utf-8"
    )
    invocation = invoke(["pack", "--recommended-run", trained.name])

    assert (
        invocation.code,
        f"Line 1 of {episodes} holds no episode" in invocation.log,
        ReleaseManifest.folder.exists()
    ) == (1, True, False)
