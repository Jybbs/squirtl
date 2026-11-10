"""
Holds the parameters each command reading a run shares:

- `RunDirectory`, naming a run's directory
- `ReleaseTag`, naming a release by its tag
- `Selection`, the flags selecting among a release's runs
"""

from cyclopts import Parameter
from pathlib  import Path
from typing   import Annotated

from squirtl.releases.schemas import Selector

type ReleaseTag = Annotated[
    str | None, Parameter(help="The tag of the release to read the runs from.")
]
type RunDirectory = Annotated[Path, Parameter(
    help = "The run's directory under `data/runs/`."
)]
type Selection = Annotated[Selector | None, Parameter(name="*")]
