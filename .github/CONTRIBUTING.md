# Contributing

Every change to *SquiRtL* starts as an issue, lands on a branch linked to it, and reaches `main` as one squashed pull request, which the notes GitHub generates for the next release then list under its labels. This page sets out the conventions each of those steps keeps, whereas the README covers installing the pinned tools and lists the tasks the development loop runs.

---

## 🕹️ From Issue to Release

| **Stage** | **Where It Lives** | **What It Carries** |
|---|---|---|
| Issue | *GitHub Issues, opened from the `Issue spec` or the `Bug` template, in the open milestone* | The problem, what has to change, and a label for each area the work reaches |
| Branch | *`N/slug`, cut from `main` and linked to issue `N`, its slug at most three terms from the issue's title* | The commits |
| Pull request | *`[N]` and the issue's title, opened from the template* | The review, and the `🎒 Brief` check the `main` ruleset requires |
| Squash merge | *`main`* | One commit per pull request, titled with the pull request's title and carrying its body |
| Release | *GitHub Releases* | The notes GitHub generates from the merged pull requests, sorted by label |

---

## 🎒 Labels

`.github/labels.toml` declares every label by its name, its color, and a one-line description, and `.github/release.yml` files each one under exactly one release-notes category, with the `*` category last to catch each pull request no earlier category matches. A label is added, renamed, or recolored in those two files within one pull request rather than in the repository's settings.

`mise labels` then writes to GitHub each label the registry declares that the repository lacks or carries under another color or description. It also lists each label the repository carries that the registry leaves out, which stays on GitHub until someone adds it to the registry or deletes it by hand.

---

## 🪻 Code Style

The package under `src/squirtl/`, its tests, and the Python task scripts under `.mise/tasks/` follow the conventions below:

- `mise format` rewrites the Python source to the house style the `[tool.prose]` table in `pyproject.toml` sets, and `mise lint` reports every rewrite the formatter would make and every lint finding without changing a file, so a lint finding is fixed by hand in the source
- A construct whose layout carries meaning the formatter cannot see, such as a matrix written row by row, is held out of the rewrites that would reshape it by a `# prose: skip` trailing its opening line. The formatter reads no rule name bracketed after that marker, so `# prose: skip[reflow-collections]` holds out the same rewrites a bare marker does, and every lint rule still fires beside it
- A lint finding on such a shape is held out instead by a `# prose: ignore[<rule>]` trailing the line it reports, which silences the one rule its brackets name and leaves every other finding standing
- Every module, function, and class carries a multi-line docstring whose first sentence starts on the verb of the operation in the third person (*"Names the release whose ROM the cartridge holds"*) or, on a record, names what the record holds. A `#` comment lands only where the code cannot say on its own what a reader needs, such as the shape and dtype of a tensor, which no annotation carries
- Every function carries type hints on its signature, and `mise lint` reports any parameter or returned value left without one. An annotation takes the built-in generics and `|` unions (*`list[str]`, `int | None`*) over the `typing` equivalents, which `mise format` rewrites into that form on its own
- A hand-rolled loop, schedule, buffer, wrapper, or statistic is checked against what the standard library, Pydantic, cyclopts, PyTorch, NumPy, and PyBoy already expose, in the versions `uv.lock` resolves, before it lands
- A setting is one field of the settings record its subject declares, such as `EmulatorSettings`, which `RunSettings` holds under the subject's name, unless it applies to the whole run, as `seed` does, and sits on `RunSettings` itself. Each carries a default and a docstring, which a command's `--help` prints beside its flag. A command reading the settings takes a subject's setting for one run from its `--<subject>.<field>` flag, with the field's underscores written as hyphens (*`--emulator.open-window`*), and for every run from the same key under `[tool.squirtl.<subject>]` in `pyproject.toml`, where a flag wins over the table
- No game file enters the repository, meaning no ROM, no save, and no file taken from the game, whether as a fixture or beside the code, since each contributor supplies their own ROM. It sits at `data/rom.gb`, the path a run reads by default, which `.gitignore` keeps out of `git status` as it does every `.gb`, `.gbc`, `.ram`, `.rtc`, `.sav`, and `.state` file, and a test needing a cartridge writes one holding no game into its temporary directory

---

## 👟 Committing

Every commit on a branch takes the conventional shape, its body one hyphen bullet per thematic change:

```
type(scope): concise description

- First thematic change
- Second thematic change
```

| **Part** | **Rule** |
|---|---|
| Type | `feat`, `fix`, `refactor`, `chore`, `docs`, or `test` |
| Scope | The subpackage of `src/squirtl/` the change lands in, or `docs`, `build`, or `ci` for a change outside the package |
| Title | Lowercase after the prefix |
| Body | Each bullet opening on a verb and running near fifteen words, with a lone bullet folded into the title instead |

---

## 🧵 Opening a Pull Request

GitHub fills the body from `.github/PULL_REQUEST_TEMPLATE.md`, whose comments name what each section holds, and GitHub requests a review from the owner `.github/CODEOWNERS` names. The pull request takes the issue's labels and milestone, and its body closes the issue it was built for.

Every pull request runs the checks below in the `🕹️ CI` workflow, each of which the command beside it reproduces on a laptop:

| **Check** | **Local Command** | **Fails When** |
|---|---|---|
| `💾 Lockfile` | `mise lockfile` | `uv.lock`, a task script's lockfile, or `.mise/mise.lock` drifts from its manifest, or a tool the project pins has no entry in `.mise/mise.lock` to install from |
| `🪻 Prose` | `mise lint` | The formatter reports a rewrite it would make or a lint finding, each one an annotation on the pull request |
| `🏟️ Suite` | `mise coverage` | A test fails, or the suite's coverage of `src/squirtl/` falls below the **95%** that `fail_under` sets in `pyproject.toml` |
| `🗝️ Workflows` | `mise run gha:lint` | zizmor reports a finding in a workflow or the composite action under `.github/`, each one an annotation on the line it concerns, or cannot parse a file there |
| `🎒 Brief` | `mise ci` | Any row above fails |

The `main` ruleset requires `🎒 Brief` alone, on a branch up to date with `main`, and `mise ci` runs every row above it in one sweep before a push.

---

## 🔧 Repository Settings

The protection on `main` and on every tag lives in `.github/rulesets/`, and the repository's features, merge methods, security features, and Actions permissions live in `.github/settings.toml`, one table per REST endpoint beside a `[dependabot]` table keyed by each endpoint it turns on or off. `mise rulesets` sends each ruleset, updating the one GitHub carries under the same name in place, and then every setting, reading the description, the homepage, and the topics from `[project]` in `pyproject.toml`. Both `mise labels` and `mise rulesets` print every command they would send and ask before sending any.

---

## 📕 Citing

`CITATION.cff` at the repository's root holds the citation GitHub offers under *"Cite this repository"*.
