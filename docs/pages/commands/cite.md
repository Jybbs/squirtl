# `squirtl cite`

Prints the footnote definition of each given key in the order given, a blank line between two, for the body of an issue or a pull request.

A key that `docs/references.bib` does not declare and a file that fails to read each exit 1, and a call naming no key exits 2, each printing no definition.

```console
squirtl cite KEYS
```

## Settings

| **Flag** | **Default** | **What It Sets** |
|---|---|---|
| `KEYS`, `--keys` | *required* | *The keys to print, each a lowercase surname and year.* |
