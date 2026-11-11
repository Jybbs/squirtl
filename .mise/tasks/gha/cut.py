#!/usr/bin/env python3
# MISE description = "Create or refresh the draft release and check the runs it lists"
"""
Keeps the draft release for the version `pyproject.toml` carries current,
as the `gha:cut` task the `🕹️ Draft` job of `🕹️ Draft` runs on the runner's
own interpreter and the `gh` it carries. `Draft` reads every release the
repository holds as a `Release`, creates a draft where none carries the
version, refreshes the generated notes of the draft that does, and fails
where a published release carries it. The task then writes the path it took,
the release's address, and the version to the step's outputs, and fails
where the runs the draft's manifest lists differ from the runs `docs/runs/`
commits.
"""

from contextlib  import nullcontext
from dataclasses import dataclass, fields
from json        import dumps, loads
from operator    import attrgetter
from os          import environ
from pathlib     import Path
from subprocess  import run
from tomllib     import load
from typing      import ClassVar, Self


def github(*arguments: str, body: str | None = None) -> str:
    """
    Runs `gh` with `arguments`, handing it `body` on standard input, and
    stops the task with an error annotation carrying what `gh` reported
    where it fails.

    Returns:
        What `gh` printed to standard output.
    """
    called = run(["gh", *arguments], capture_output=True, input=body, text=True)

    if called.returncode:
        raise SystemExit(
            f"::error::gh {' '.join(arguments[:2])} failed, {called.stderr.strip()}"
        )

    return called.stdout


@dataclass(frozen=True, kw_only=True)
class Release:
    """
    One release the repository holds, a draft or a published one, holding
    the fields the REST API lists for it under the names GitHub gives them.
    """

    manifest: ClassVar[str] = "manifest.json"

    assets           : list[dict]
    body             : str | None
    draft            : bool
    id               : int
    tag_name         : str
    target_commitish : str

    @property
    def attached(self) -> set[str]:
        """
        Reads the name of each trained run the release's manifest lists,
        downloading the asset `manifest` names by its id, or none where the
        release attaches no such asset.
        """
        asset = next(
            (asset for asset in self.assets if asset["name"] == self.manifest),
            None
        )

        if asset is None:
            return set()

        listing = github(
            "api",
            f"repos/{{owner}}/{{repo}}/releases/assets/{asset['id']}",
            "--header",
            "Accept: application/octet-stream"
        )

        return {run["name"] for run in loads(listing)["runs"]}

    @property
    def context(self) -> str:
        """
        Reads what sits above the notes GitHub generated, which open on an
        HTML comment naming the configuration they came from, or the whole
        body where no such comment remains.
        """
        return (self.body or "").partition("<!-- Release notes generated")[0]

    def refresh(self) -> str:
        """
        Replaces everything below the release's context with the notes
        GitHub generates for its tag against the branch the release targets
        as it stands, leaving the context and the tag as they were.

        Returns:
            The release's address as the edit leaves it.
        """
        notes = loads(
            github(
                "api",
                "repos/{owner}/{repo}/releases/generate-notes",
                "--raw-field",
                f"tag_name={self.tag_name}",
                "--raw-field",
                f"target_commitish={self.target_commitish}"
            )
        )["body"]

        # Resends `tag_name`, since an update omitting it removes the release's tag.
        return loads(
            github(
                "api",
                f"repos/{{owner}}/{{repo}}/releases/{self.id}",
                "--method",
                "PATCH",
                "--input",
                "-",
                body = dumps({"body": self.context + notes, "tag_name": self.tag_name})
            )
        )["html_url"]


@dataclass(frozen=True, kw_only=True)
class Draft:
    """
    The draft release for the version `pyproject.toml` carries, beside every
    release the repository holds.
    """

    folder: ClassVar[Path] = Path("docs/runs")

    committed : set[str]
    releases  : list[Release]
    version   : str

    @property
    def release(self) -> Release | None:
        """
        Finds the release carrying the version, a published one ahead of a
        draft sharing its tag.

        Returns:
            That release, or `None` where no release carries the version.
        """
        return min(
            (release for release in self.releases if release.tag_name == self.version),
            default = None,
            key     = attrgetter("draft")
        )

    def create(self) -> str:
        """
        Creates a draft for the version through `gh release create`, titled
        with the bare version and its notes generated against `main`, the
        branch GitHub writes the tag on once the draft is published.

        Returns:
            The draft's address.
        """
        return github(
            "release",
            "create",
            "--draft",
            "--generate-notes",
            "--target",
            "main",
            "--title",
            self.version,
            self.version
        ).strip()

    @classmethod
    def from_github(cls) -> Self:
        """
        Reads the version from `pyproject.toml`, the name of each run
        directory `folder` holds, and every release the repository holds
        through one listing of every page, asking for each field `Release`
        declares.
        """
        with Path("pyproject.toml").open("rb") as manifest:
            version = load(manifest)["project"]["version"]

        listing = github(
            "api",
            "repos/{owner}/{repo}/releases",
            "--paginate",
            "--jq",
            f".[] | {{{', '.join(field.name for field in fields(Release))}}}"
        )

        return cls(
            committed = {directory.name for directory in cls.folder.iterdir()},
            releases  = [Release(**loads(line)) for line in listing.splitlines()],
            version   = version
        )

    def maintain(self):
        """
        Creates the draft where no release carries the version and refreshes
        the draft that does, then writes the path taken, the release's
        address, and the version to the file `GITHUB_OUTPUT` names, or
        prints them where that variable is unset. It then stops the task
        with one error annotation naming each run `committed` holds that the
        draft's manifest leaves out and another naming each run the manifest
        lists that `committed` leaves out, a created draft attaching no
        manifest. Where a published release carries the version, it stops
        the task first, with an error annotation naming `mise bump`.
        """
        match self.release:
            case None: state, url, attached = "created", self.create(), set()
            case Release(draft=True) as release:
                state, url, attached = "refreshed", release.refresh(), release.attached
            case Release():
                raise SystemExit(
                    f"::error::{self.version} is already published, "
                    "so run `mise bump` to open the next version"
                )

        path = environ.get("GITHUB_OUTPUT")

        with open(path, "a", encoding="utf-8") if path else nullcontext() as outputs:
            print(
                f"state={state}",
                f"url={url}",
                f"version={self.version}",
                file = outputs,
                sep  = "\n"
            )

        manifest       = f"manifest of the draft release for {self.version}"
        missing, stray = (
            ", ".join(sorted(runs))
            for runs in (self.committed - attached, attached - self.committed)
        )

        if annotations := [
            f"::error::{sentence}, so run `mise attach`"
            for sentence in (
                missing and (
                    f"docs/runs/ commits {missing}, which the {manifest} "
                    "leaves out"
                ),
                stray and f"The {manifest} lists {stray}, which docs/runs/ leaves out"
            )
            if sentence
        ]:
            raise SystemExit("\n".join(annotations))


if __name__ == "__main__":

    Draft.from_github().maintain()
