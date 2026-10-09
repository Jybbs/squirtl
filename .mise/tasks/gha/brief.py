#!/usr/bin/env -S uv run --exact --locked --script
# MISE description = "Write the workflow step summary and exit with the gate's verdict"
# /// script
# dependencies    = ["minijinja==2.24.0"]
# requires-python = ">=3.14"
# ///
"""
Writes the step summary of a workflow run and exits with the verdict of
the jobs its `🎒 Brief` gate waited on, as the `gha:brief` task every gate
job runs. `Brief` reads each job it waited on as a `Job` and fills in the
template `.github/scripts/summaries/` holds under the name of the running
workflow's file, or `base.md.j2` where it holds none. The task exits 1 where
any job ended in anything but success.
"""

from contextlib  import nullcontext
from dataclasses import dataclass
from json        import loads
from minijinja   import Environment, load_from_path
from os          import environ
from pathlib     import Path
from typing      import Self


@dataclass(frozen=True, kw_only=True)
class Brief:
    """
    The gate a workflow ends on, holding the `needs` context of the jobs it
    waited on beside what the runner's variables say about the workflow run.
    """

    commit     : str
    file       : Path
    needs      : dict[str, Job]
    ref        : str
    repository : str
    server     : str
    workflow   : str

    @property
    def passed(self) -> bool:
        """
        Tells whether every job the gate waited on succeeded.
        """
        return all(job.succeeded for job in self.needs.values())

    @property
    def reports(self) -> dict[str, str]:
        """
        Collects the address of each coverage report the workflow run
        attached, read from every job output whose name ends in `coverage`.

        Returns:
            Each report's output name beside the address of its artifact.
        """
        return {
            name: url
            for job in self.needs.values()
            for name, url in job.outputs.items()
            if name.endswith("coverage")
        }

    @property
    def summary(self) -> str:
        """
        Fills in the workflow's template from the gate's fields, its
        verdict, and the reports the workflow run attached.
        """
        summaries = Path(".github/scripts/summaries")
        named     = self.file.with_suffix(".md.j2").name

        return Environment(
            keep_trailing_newline = True,
            loader                = load_from_path(summaries),
            lstrip_blocks         = True,
            trim_blocks           = True,
            undefined_behavior    = "strict"
        ).render_template(
            named if (summaries / named).is_file() else "base.md.j2",
            **vars(self),
            passed  = self.passed,
            reports = self.reports
        )

    @classmethod
    def from_environment(cls) -> Self:
        """
        Reads the gate of the running workflow from `NEEDS`, the `needs`
        context as JSON, and from the variables the runner sets. The
        commit comes from `COMMIT`, which `🕹️ CI` sets to the head of a pull
        request's branch, and from `GITHUB_SHA` where `COMMIT` is unset
        or empty.
        """
        return cls(
            commit = environ.get("COMMIT") or environ["GITHUB_SHA"],
            file   = Path(environ["GITHUB_WORKFLOW_REF"].partition("@")[0]),
            needs  = {
                name: Job(**job) for name, job in loads(environ["NEEDS"]).items()
            },
            ref        = environ.get("GITHUB_HEAD_REF") or environ["GITHUB_REF_NAME"],
            repository = environ["GITHUB_REPOSITORY"],
            server     = environ["GITHUB_SERVER_URL"],
            workflow   = environ["GITHUB_WORKFLOW"]
        )

    def write(self) -> int:
        """
        Appends the summary to the file `GITHUB_STEP_SUMMARY` names, or
        prints it where that variable is unset.

        Returns:
            The gate's verdict as an exit status.
        """
        path = environ.get("GITHUB_STEP_SUMMARY")

        with open(path, "a", encoding="utf-8") if path else nullcontext() as page:
            print(self.summary, end="", file=page)

        return 0 if self.passed else 1


@dataclass(frozen=True, kw_only=True)
class Job:
    """
    One job a gate waited on, holding the fields the `needs` context gives
    it under the names GitHub gives them.
    """

    outputs : dict[str, str]
    result  : str

    @property
    def succeeded(self) -> bool:
        """
        Tells whether the job ended in success, a skipped or cancelled job
        counting as one that did not.
        """
        return self.result == "success"


if __name__ == "__main__":

    raise SystemExit(Brief.from_environment().write())
