"""
Pins what `squirtl fetch` does, covering:

- Each run of the latest release, or of the release `--release` names,
  unpacked into `data/runs/` and logged, and nothing downloaded for a run
  already there
- A selection matching no run, and a release attaching no manifest, each
  exiting 1
"""

from common.cli      import Invoker
from common.releases import ADDRESS, GitHub
from json            import dumps
from pathlib         import Path
from pytest          import mark, param

from squirtl.runs.schemas import Run


@mark.parametrize(
    "flags",
    [
        param([],                                    id="the-latest"),
        param(["--release", "0.2.0", "--seed", "1"], id="a-selection")
    ]
)
def test_a_fetch_unpacks_each_run_it_selects_and_logs_it(
    flags    : list[str],
    github   : GitHub,
    invoke   : Invoker,
    released : Path
):
    """
    Asserts that fetching the latest release, or the one `--release` names
    under a selection matching the run, exits zero, unpacking the run where
    it packed from behind a progress bar bearing its tar's name and logging
    its directory, and that fetching again downloads no tar.
    """
    invocation = invoke(["fetch", *flags])

    assert (invocation.code, invocation.messages[-1]) == (0, f"Fetched {released}")
    assert f"{released.name}.tar.zst" in invocation.log
    assert Run.read(released).name == released.name

    github.served = {
        address: body
        for address, body in github.served.items()
        if not address.endswith(".tar.zst")
    }

    assert invoke(["fetch", *flags]).code == 0


@mark.parametrize(
    ("flags", "reason"),
    [
        param(
            ["--seed", "99"],
            "No run of the release 0.2.0 matches",
            id = "no-match"
        ),
        param(
            ["--release", "0.1.0"],
            "attaches no manifest.json",
            id = "no-manifest"
        )
    ]
)
def test_a_fetch_with_nothing_to_unpack_exits_1(
    flags    : list[str],
    github   : GitHub,
    invoke   : Invoker,
    reason   : str,
    released : Path
):
    """
    Asserts that a selection matching none of the release's runs, and a
    release attaching no manifest, each exit 1, logging the reason and
    unpacking nothing.
    """
    github.served[f"{ADDRESS}/tags/0.1.0"] = dumps(
        {"published_at": "2026-10-01T00:00:00Z", "tag_name": "0.1.0"}
    ).encode()
    invocation = invoke(["fetch", *flags])

    assert (invocation.code, reason in invocation.log, released.exists()) == (
        1, True, False
    )
