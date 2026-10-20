"""
Defines the checks `repo:audit` runs, each a `Check` whose `scan` yields one
`Finding` for each divergence it reads across the files of the checkout, and
`Audit`, which runs every check and prints each finding as an annotation.
"""

from abc             import ABC, abstractmethod
from ast             import AsyncFunctionDef, ClassDef, FunctionDef, get_docstring, parse, walk
from collections     import Counter, defaultdict
from collections.abc import Callable, Iterator
from functools       import cache
from itertools       import chain, compress
from json            import dumps
from operator        import methodcaller
from packaging.specifiers import SpecifierSet
from packaging.version    import Version
from re     import fullmatch
from typing import ClassVar, Self

from squirtl.repo.github  import Schema
from squirtl.repo.schemas import (
    Actions, Citation, Finding, Labels, License, Lockfile, Manifest, MiseConfig,
    Project, ReleaseNotes, Rulesets, Scripts, Severity, Tasks, Templates, Tree,
    Unreadable, Workflows
)


class Audit(Schema):
    """
    The findings of every check `Check` declares, each finding held once
    however many checks report it.
    """

    findings: tuple[Finding, ...]
    """
    Every finding, in the order the checks report them.
    """

    @classmethod
    def read(cls) -> Self:
        """
        Runs every check, reading each file once however many checks read
        it, and takes the findings reporting a file that fails to parse in
        place of the findings a check reading that file would report after
        it, keeping each one the check reported before.
        """
        documents = cache(methodcaller("read"))
        findings  = {}

        for kind in Check.__subclasses__():
            try:
                for finding in kind.read(documents).scan():
                    findings[finding] = None
            except Unreadable as error:
                findings |= dict.fromkeys(error.args)

        return cls(findings=tuple(findings))

    def report(self) -> int:
        """
        Prints each finding as an annotation, or a line saying every check
        passed where none diverges.

        Returns:
            The exit status, which is 1 where any finding is an error and 0
            otherwise.
        """
        annotations = "\n".join(finding.annotation for finding in self.findings)

        print(annotations or "Every check passed")
        return int(any(finding.severity is Severity.ERROR for finding in self.findings))


class Check(Schema, ABC):
    """
    The base of one check `repo:audit` runs, each field the record of the
    files the check reads, which `read` builds from the reader it is handed.
    """

    @classmethod
    def read(cls, documents: Callable[[type], Schema]) -> Self:
        """
        Builds the check from the record `documents` reads for each field's
        type, a reader a caller running several checks shares so each file
        is read once.
        """
        fields = cls.model_fields.items()
        return cls(**{name: documents(field.annotation) for name, field in fields})

    @abstractmethod
    def scan(self) -> Iterator[Finding]:
        """
        Yields one finding for each divergence the check reads.
        """


class Anchors(Check):
    """
    Fails on each anchor or alias an action manifest carries, since GitHub's
    parser of action manifests refuses both, whereas a workflow file may
    carry them.
    """

    actions: Actions

    def scan(self) -> Iterator[Finding]:
        """
        Yields a finding on each line of a manifest carrying an anchor or
        an alias.
        """
        for action in self.actions.actions:
            for line in action.anchors:
                yield Finding(
                    file    = action.path,
                    line    = line,
                    message = (
                        f"`{action.path}` carries a YAML anchor or alias, which "
                        "GitHub's parser of action manifests refuses"
                    )
                )


class Attribution(Check):
    """
    Holds each license file and `CITATION.cff` to the license, the authors,
    the name, and the version `[project]` declares.
    """

    citation : Citation
    project  : Project

    def scan(self) -> Iterator[Finding]:
        """
        Yields a finding for a license file titled for another license
        or whose copyright line leaves out an author, and for each title,
        version, license, or author `CITATION.cff` names that the manifest
        does not, a value compared without regard to case so the title may
        style the name the package installs under.
        """
        project  = self.project
        citation = self.citation.path
        authors  = self.citation.authors
        expected = {
            "license" : project.license,
            "title"   : project.name,
            "version" : str(project.version)
        }

        for path in project.license_files:
            license = License.from_path(path)

            if license.title != f"{project.license} License":
                yield Finding(
                    file    = path,
                    line    = 1,
                    message = (
                        f"`{path}` is titled {license.title!r}, whereas "
                        f"`[project].license` is `{project.license}`"
                    )
                )

            for name in project.credits:
                if name not in (license.holders or ""):
                    yield Finding.locate(
                        path,
                        "Copyright",
                        message = (
                            f"The copyright line of `{path}` leaves out {name}, "
                            "whom `[project].authors` names"
                        )
                    )

        for key, value in expected.items():
            field = self.citation.root.at(key)

            if field and str(field.value).casefold() != value.casefold():
                yield Finding(
                    file    = citation,
                    line    = field.line,
                    message = (
                        f"`{citation}` names the {key} {field.value!r}, whereas "
                        f"`[project]` declares {value!r}"
                    )
                )

        for name, line in authors.items():
            if name not in project.credits:
                yield Finding(
                    file    = citation,
                    line    = line,
                    message = (
                        f"`{citation}` credits {name}, whom `[project].authors` "
                        "leaves out"
                    )
                )

        for name in project.credits:
            if name not in authors:
                yield Finding.locate(
                    citation,
                    "authors",
                    message = (
                        f"`{citation}` leaves out {name}, whom `[project].authors` "
                        "names"
                    )
                )


class Commits(Check):
    """
    Holds every action the workflows and the action manifests run to one
    commit, wherever it is pinned.
    """

    actions   : Actions
    workflows : Workflows

    def scan(self) -> Iterator[Finding]:
        """
        Yields a finding on each step pinning an action that another step
        pins to a different commit.
        """
        pins = defaultdict(lambda: defaultdict(list))

        for path, step in chain(self.workflows.steps, self.actions.steps):
            if pinned := step.pinned:
                action, commit = pinned
                pins[action][commit].append((path, step.line))

        for action, commits in pins.items():
            for commit, homes in commits.items():
                others = ", ".join(f"`{other}`" for other in commits if other != commit)

                for path, line in homes if others else []:
                    yield Finding(
                        file    = path,
                        line    = line,
                        message = (
                            f"`{action}` is pinned to `{commit}` here and to "
                            f"{others} elsewhere"
                        )
                    )


class Docstrings(Check):
    """
    Fails on each module, class, and function in the Python of the checkout
    that carries no docstring.
    """

    tree: Tree

    def scan(self) -> Iterator[Finding]:
        """
        Yields a finding on each definition with no docstring in each `.py`
        file git lists, raising `Unreadable` on a file that fails to parse.
        """
        for file in self.tree.files:
            if file.suffix != ".py":
                continue

            with Finding.reading(file):
                module = parse(file.read_text(encoding="utf-8"), filename=file)

            if get_docstring(module) is None:
                yield Finding(
                    file    = file,
                    line    = 1,
                    message = f"The module `{file}` carries no docstring"
                )

            for node in walk(module):
                if (
                    isinstance(node, AsyncFunctionDef | ClassDef | FunctionDef)
                    and get_docstring(node) is None
                ):
                    yield Finding(
                        file    = file,
                        line    = node.lineno,
                        message = f"`{node.name}` in `{file}` carries no docstring"
                    )


class Gates(Check):
    """
    Holds every workflow to the one gate it ends on, the job running `task`,
    which waits on every other job whatever their results, and holds each
    check a ruleset requires to the name of a pull-request workflow's gate.
    """

    task: ClassVar[str] = "gha:brief"

    rulesets  : Rulesets
    workflows : Workflows

    def scan(self) -> Iterator[Finding]:
        """
        Yields a finding for a workflow running `task` in no job or in more
        than one, for a gate setting no name, running under another `if`
        than `always()`, or waiting on fewer than every other job, and for a
        required check no pull-request workflow's gate reports.
        """
        reported = set()

        for workflow in self.workflows.workflows:
            path  = workflow.path
            jobs  = workflow.jobs
            gates = [job for job in jobs if self.task in job.tasks]

            if not gates:
                yield Finding(
                    file    = path,
                    line    = (workflow.root.at("jobs") or workflow.root).line,
                    message = (
                        f"`{path}` ends on no gate, since no job runs "
                        f"`{self.task}`"
                    )
                )

            count = len(gates)

            for gate in gates:
                missing = sorted({job.key for job in jobs} - {gate.key, *gate.needs})
                faults  = {
                    "lacks `if: always()`, so a failed job skips it": not gate.always,
                    "sets no name for a ruleset to require": not gate.get("name"),
                    f"is one of {count} jobs running `{self.task}`" : count > 1,
                    f"waits on no {', '.join(missing)}"             : bool(missing)
                }

                for fault in compress(faults, faults.values()):
                    yield Finding(
                        file    = path,
                        line    = gate.line,
                        message = f"The gate `{gate.key}` {fault}"
                    )

                if workflow.pulls and (name := gate.get("name")):
                    reported.add(name)

        for path, ruleset in self.rulesets.rulesets.items():
            for check in ruleset.checks:
                if check not in reported:
                    yield Finding.locate(
                        path,
                        dumps(check, ensure_ascii=False),
                        message = (
                            f"`{ruleset.name}` requires the check {check!r}, which "
                            "no gate of a pull-request workflow reports"
                        )
                    )


class Inputs(Check):
    """
    Holds each input a step passes an action of this repository to the
    inputs the action's manifest declares, since GitHub only warns about an
    undeclared input before running the action on its defaults.
    """

    actions   : Actions
    workflows : Workflows

    def scan(self) -> Iterator[Finding]:
        """
        Yields a finding on each input a step passes that the manifest of
        the action it uses leaves out.
        """
        manifests = self.actions.manifests

        for path, step in chain(self.workflows.steps, self.actions.steps):
            action = manifests.get(step.local)

            for name, value in step.fields("with").items() if action else []:
                if name not in action.inputs:
                    yield Finding(
                        file    = path,
                        line    = value.line,
                        message = f"`{name}` is no input `{action.path}` declares"
                    )


class LabelCheck(Check):
    """
    Holds the label registry to the release-notes categories and the issue
    templates naming its labels, and each label to a name and a color no
    other label shares.
    """

    labels    : Labels
    notes     : ReleaseNotes
    templates : Templates

    def scan(self) -> Iterator[Finding]:
        """
        Yields a finding for a name or a color two labels share, for a label
        a category or a template names that the registry does not declare,
        and for a declared label sitting in no category or in more than one,
        leaving out the `*` category, which catches every pull request no
        earlier category files.
        """
        declared = self.labels.names
        filed    = Counter()

        for kind in ("name", "color"):
            shared = Counter(getattr(label, kind) for label in self.labels.labels)

            for value, count in shared.items():
                if count > 1:
                    yield Finding.locate(
                        Labels.file,
                        f'"{value}"',
                        message = f"{count} labels share the {kind} `{value}`"
                    )

        for category in self.notes.categories:
            filed.update(labels := category.get("labels", default=[]))

            for label in labels:
                if label != "*" and label not in declared:
                    yield Finding(
                        file    = self.notes.path,
                        line    = category.line,
                        message = (
                            f"The release-notes category {category.get('title')!r} "
                            f"names `{label}`, which `{Labels.file}` does not declare"
                        )
                    )

        for name in sorted(declared):
            if filed[name] != 1:
                yield Finding.locate(
                    Labels.file,
                    f'"{name}"',
                    message = (
                        f"`{name}` sits in {filed[name]} release-notes categories "
                        "rather than one"
                        if filed[name]
                        else f"`{name}` sits in no release-notes category"
                    )
                )

        for template in self.templates.templates:
            for label in template.labels:
                if label not in declared:
                    yield Finding(
                        file    = template.path,
                        line    = (template.root.at("labels") or template.root).line,
                        message = (
                            f"`{template.path}` sets `{label}`, which "
                            f"`{Labels.file}` does not declare"
                        )
                    )


class Layout(Check):
    """
    Holds the package to the layout its subjects follow, meaning every
    module inside a subpackage, no `__init__.py` beside the one an
    entry point names, each module and subpackage named for its role in
    `snake_case` and never `utils`, and each test module mirroring a module.
    """

    # `unmirrored` holds the test modules that mirror no module by design,
    # meaning the task tests, the command line's smoke test, and the
    # isolation tests.
    unmirrored: ClassVar[tuple[str, ...]] = (
        "tests/cli/app.py", "tests/isolation.py", "tests/tasks/**"
    )

    manifest : Manifest
    project  : Project
    tree     : Tree

    def scan(self) -> Iterator[Finding]:
        """
        Yields a finding for each module at the root of a package, each
        `__init__.py` no entry point names, each module or subpackage named
        outside `snake_case` or named `utils`, and each test module pytest
        collects that mirrors no module and that `unmirrored` leaves out.
        """
        files   = set(self.tree.files)
        entries = {
            package.parent.joinpath(*module.split("."), "__init__.py")
            for package in self.manifest.packages
            for module in self.project.entries
        }

        for package in self.manifest.packages:
            for module in self.tree.under(package):
                if module.suffix != ".py":
                    continue

                if module.parent == package:
                    yield Finding(
                        file    = module,
                        message = (
                            f"`{module}` sits at the root of `{package}`, outside "
                            "every subpackage"
                        )
                    )

                if module.name == "__init__.py" and module not in entries:
                    yield Finding(
                        file    = module,
                        message = (
                            f"`{module}` makes a package no entry point names, "
                            "whereas every other subpackage is a namespace package"
                        )
                    )

                for part in module.relative_to(package).with_suffix("").parts:
                    if part == "utils":
                        yield Finding(
                            file    = module,
                            message = (
                                f"`{part}` in `{module}` names no role a reader "
                                "can find"
                            )
                        )

                    elif part != "__init__" and not fullmatch(
                        r"[a-z][a-z0-9]*(_[a-z0-9]+)*",
                        part
                    ):
                        yield Finding(
                            file    = module,
                            message = f"`{part}` in `{module}` is not `snake_case`"
                        )

        for test in self.tree.files:
            if (
                self.manifest.collects(test)
                and not any(test.full_match(pattern) for pattern in self.unmirrored)
                and files.isdisjoint(self.manifest.mirrors(test))
            ):
                yield Finding(
                    file    = test,
                    message = f"`{test}` mirrors no module of the package"
                )


class Pins(Check):
    """
    Holds the Python and the uv `.mise/config.toml` pins to each manifest
    key repeating them, and each build requirement and build constraint the
    manifest declares to an exact pin.
    """

    manifest : Manifest
    mise     : MiseConfig
    project  : Project

    def scan(self) -> Iterator[Finding]:
        """
        Yields a finding for a `requires-python` opening on another minor
        than the Python mise pins, a `target-version` naming another minor,
        a `required-version` admitting another uv than the one mise pins,
        and each build requirement or constraint that pins no exact version
        through one `==` specifier.
        """
        file    = Manifest.file
        python  = self.mise.python
        minor   = f"{python.major}.{python.minor}"
        uv      = SpecifierSet(f"=={self.mise.uv}")
        pinning = f"the Python {python} `{MiseConfig.file}` pins makes it"
        floors  = {
            Version(specifier.version).release[:2]
            for specifier in self.project.requires_python
            if specifier.operator == ">="
        }

        if floors != {python.release[:2]}:
            yield Finding.locate(
                file,
                "requires-python",
                message = (
                    f"`requires-python` is `{self.project.requires_python}`, "
                    f"whereas {pinning} `>={minor}`"
                )
            )

        if self.manifest.target_version != minor:
            yield Finding.locate(
                file,
                "[tool.prose]",
                "target-version",
                message = (
                    f"`target-version` is `{self.manifest.target_version}` under "
                    f"`[tool.prose]`, whereas {pinning} `{minor}`"
                )
            )

        if self.manifest.uv_version != uv:
            yield Finding.locate(
                file,
                "[tool.uv]",
                "required-version",
                message = (
                    f"`required-version` is `{self.manifest.uv_version}` under "
                    f"`[tool.uv]`, whereas the uv {self.mise.uv} `{MiseConfig.file}` "
                    f"pins makes it `{uv}`"
                )
            )

        for key, requirements in (
            ("[build-system]", self.manifest.build_requirements),
            ("build-constraint-dependencies", self.manifest.build_constraints)
        ):
            for requirement in requirements:
                match list(requirement.specifier):
                    case [pin] if pin.operator == "==" and "*" not in pin.version:
                        continue

                yield Finding.locate(
                    file,
                    key,
                    requirement.name,
                    message = f"`{requirement}` under `{key}` pins no exact version"
                )


class Rows(Check):
    """
    Holds the tasks the pull-request rows run to the tasks `sweep` depends
    on, so `mise ci` runs on a laptop what every pull request runs.
    """

    sweep: ClassVar[str] = "repo:ci"

    tasks     : Tasks
    workflows : Workflows

    def scan(self) -> Iterator[Finding]:
        """
        Yields a finding for each task a job of a pull-request workflow runs
        that `sweep` does not depend on, gates left aside, and for each task
        `sweep` depends on that no such job runs.
        """
        sweep = self.tasks.named.get(self.sweep)
        rows  = {
            task: (workflow.path, job.line)
            for workflow in self.workflows.workflows
            if workflow.pulls
            for job in workflow.jobs
            if Gates.task not in job.tasks
            for task in job.tasks
        }

        if sweep is None:
            yield Finding(
                file    = MiseConfig.file,
                message = f"mise lists no `{self.sweep}` task"
            )
            return

        for task, (path, line) in rows.items():
            if task not in sweep.depends:
                yield Finding(
                    file    = path,
                    line    = line,
                    message = (
                        f"A pull-request row runs `{task}`, which `{self.sweep}` "
                        "does not depend on"
                    )
                )

        for task in sweep.depends:
            if task not in rows:
                yield Finding.locate(
                    sweep.file,
                    "depends",
                    message = (
                        f"`{self.sweep}` depends on `{task}`, which no pull-request "
                        "row runs"
                    )
                )


class Runners(Check):
    """
    Holds every job the workflows run to one runner image.
    """

    workflows: Workflows

    def scan(self) -> Iterator[Finding]:
        """
        Yields a finding on each job's `runs-on` where the workflows name
        more than one image.
        """
        images = defaultdict(list)

        for path, job in self.workflows.jobs:
            if runner := job.at("runs-on"):
                images[str(runner.value)].append((path, runner.line, job.key))

        for image, homes in images.items() if len(images) > 1 else []:
            others = ", ".join(f"`{other}`" for other in images if other != image)

            for path, line, key in homes:
                yield Finding(
                    file    = path,
                    line    = line,
                    message = (
                        f"`{key}` runs on `{image}`, whereas other jobs run on "
                        f"{others}"
                    )
                )


class ScriptCheck(Check):
    """
    Holds the inline metadata of each script under `.mise/` to the lockfile
    and the manifest it repeats, and every `uv run` a script starts to the
    flags keeping it inside the lockfile.
    """

    lockfile : Lockfile
    project  : Project
    scripts  : Scripts

    def scan(self) -> Iterator[Finding]:
        """
        Yields a finding for a script's `requires-python` other than the
        manifest's, for each package its metadata declares that `uv.lock`
        resolves at no version the declaration admits, for each `uv run`
        opening on anything but `--exact --locked`, and for a shebang
        running a script with metadata of its own without `--script` after
        them.
        """
        expected = self.project.requires_python

        for script in self.scripts.scripts:
            path     = script.path
            metadata = script.metadata

            if metadata and metadata.requires_python not in {None, expected}:
                yield Finding.locate(
                    path,
                    "requires-python",
                    message = (
                        f"`{path}` declares `requires-python` as "
                        f"`{metadata.requires_python}`, whereas `[project]` "
                        f"declares `{expected}`"
                    )
                )

            for requirement in metadata.dependencies if metadata else []:
                locked = self.lockfile.resolved(requirement.name)

                if not locked or not all(map(requirement.specifier.contains, locked)):
                    yield Finding.locate(
                        path,
                        "# /// script",
                        requirement.name,
                        message = (
                            f"`{path}` declares `{requirement}`, whereas "
                            f"`{Lockfile.file}` resolves "
                            f"{', '.join(map(str, locked)) or 'no version of it'}"
                        )
                    )

            for line, options in script.runs:
                if options[:2] != ("--exact", "--locked"):
                    yield Finding(
                        file    = path,
                        line    = line,
                        message = (
                            f"`uv run` in `{path}` opens on no "
                            "`--exact --locked`"
                        )
                    )

                elif line == 1 and metadata and options[2:3] != ("--script",):
                    yield Finding(
                        file    = path,
                        line    = line,
                        message = (
                            f"`{path}` declares its own dependencies, whereas "
                            "its shebang takes no `--script` after "
                            "`--exact --locked`"
                        )
                    )


class Subsets(Check):
    """
    Holds the tool subsets the jobs restoring a cache install to the
    subsets the warming jobs save, in both directions, each subset read as
    `jdx/mise-action` keys it, its tools sorted.
    """

    workflows: Workflows

    def scan(self) -> Iterator[Finding]:
        """
        Yields a finding for each subset a job under `cache-mode: read`
        passes the provisioning action that no job under `cache-mode: write`
        passes, and for the reverse.
        """
        modes = {"read": defaultdict(list), "write": defaultdict(list)}

        for path, job in self.workflows.jobs:
            for step, subset in job.inputs("tools") if job.cache_mode in modes else []:
                names = " ".join(sorted(subset.split()))
                modes[job.cache_mode][names].append((path, step.line, job.key))

        for mode, other, did, verb in (
            ("read", "write", "installs", "saves"),
            ("write", "read", "saves", "restores")
        ):
            for names, homes in modes[mode].items():
                for path, line, key in homes if names not in modes[other] else []:
                    yield Finding(
                        file    = path,
                        line    = line,
                        message = (
                            f"`{key}` {did} the tool subset `{names}`, which no job "
                            f"{verb}"
                        )
                    )


class Summaries(Check):
    """
    Holds the workflow run's summary to the one writer it has, the gate,
    which runs `Gates.task`, so no other job and no composite step writes
    it.
    """

    actions   : Actions
    workflows : Workflows

    def scan(self) -> Iterator[Finding]:
        """
        Yields a finding on each step that writes the summary in a job that
        runs no `Gates.task`, and on each step of a composite action that
        writes it.
        """
        for path, job in self.workflows.jobs:
            for step in job.steps if Gates.task not in job.tasks else []:
                if step.writes_summary:
                    yield Finding(
                        file    = path,
                        line    = step.line,
                        message = (
                            f"`{job.key}` writes the workflow run's summary, "
                            "which only the gate writes"
                        )
                    )

        for path, step in self.actions.steps:
            if step.writes_summary:
                yield Finding(
                    file    = path,
                    line    = step.line,
                    message = (
                        f"A step of `{path}` writes the workflow run's summary, "
                        "which only a workflow's gate writes"
                    )
                )


class TaskCheck(Check):
    """
    Reports each defect `mise tasks validate` finds in a task's definition,
    a warning as a warning.
    """

    tasks: Tasks

    def scan(self) -> Iterator[Finding]:
        """
        Yields a finding on the file declaring the task each defect sits in,
        or on `.mise/config.toml` where mise lists no such task.
        """
        for issue in self.tasks.issues:
            yield Finding(
                file    = self.tasks.declaring(issue.task),
                message = (
                    f"`{issue.task}` fails `mise tasks validate` with "
                    f"{issue.text}"
                ),
                severity = issue.severity
            )


class Warming(Check):
    """
    Holds the push filter of each workflow saving a cache to the files the
    cache's key is built from, so a push moving a key runs the workflow that
    saves the cache under the new key.
    """

    # `hashed` holds the globs `jdx/mise-action` hashes into its cache key,
    # its `MISE_CONFIG_FILE_PATTERNS`.
    hashed: ClassVar[tuple[str, ...]] = (
        "**/.config/mise/config.toml", "**/.config/mise/config.lock",
        "**/.config/mise/config.*.toml", "**/.config/mise/config.*.lock",
        "**/.config/mise.toml", "**/.config/mise.lock",
        "**/.config/mise.*.toml", "**/.config/mise.*.lock",
        "**/.mise/config.toml", "**/.mise/config.lock",
        "**/.mise/config.*.toml", "**/.mise/config.*.lock",
        "**/mise/config.toml", "**/mise/config.lock",
        "**/mise/config.*.toml", "**/mise/config.*.lock",
        "**/.mise.toml", "**/.mise.lock",
        "**/.mise.*.toml", "**/.mise.*.lock",
        "**/mise.toml", "**/mise.lock",
        "**/mise.*.toml", "**/mise.*.lock",
        "**/.tool-versions"
    )

    actions   : Actions
    tree      : Tree
    workflows : Workflows

    def scan(self) -> Iterator[Finding]:
        """
        Yields a finding for each file a cache key is built from that the
        push filter of a workflow saving the cache leaves out, meaning the
        workflow file, the manifest of each action of this repository a
        saving job runs, and each file of the checkout `hashed` matches.
        """
        manifests = self.actions.manifests
        hashed    = {
            file
            for file in self.tree.files
            if any(file.full_match(pattern) for pattern in self.hashed)
        }

        for workflow in self.workflows.workflows:
            saving = [job for job in workflow.jobs if job.cache_mode == "write"]
            on     = workflow.root.at("on") or workflow.root
            built  = {
                workflow.path,
                *hashed,
                *(
                    manifests[step.local].path
                    for job in saving
                    for step in job.steps
                    if step.local in manifests
                )
            }

            for file in sorted(built) if saving else []:
                if not workflow.pushes(file):
                    yield Finding(
                        file    = workflow.path,
                        line    = (on.at("push", "paths") or on).line,
                        message = (
                            f"`{workflow.path}` saves a cache keyed on `{file}`, "
                            "which its push filter leaves out"
                        )
                    )
