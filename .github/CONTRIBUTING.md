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

`mise ci` runs on a laptop every task a row of the `🕹️ CI` workflow runs, and the `🎒 Brief` gate that workflow ends on passes only when every row does.

---

## 🔧 Repository Settings

The protection on `main` and on every tag lives in `.github/rulesets/`, and the repository's features, merge methods, security features, and Actions permissions live in `.github/settings.toml`, one table per REST endpoint beside a `[dependabot]` table keyed by each endpoint it turns on or off. `mise rulesets` sends each ruleset, updating the one GitHub carries under the same name in place, and then every setting, reading the description, the homepage, and the topics from `[project]` in `pyproject.toml`. Both `mise labels` and `mise rulesets` print every command they would send and ask before sending any.

---

## 📕 Citing

`CITATION.cff` at the repository's root holds the citation GitHub offers under *"Cite this repository"*.
