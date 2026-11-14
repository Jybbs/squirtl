"""
Defines `SearchCheckpoint`, the file holding everything a stopped search
continues from, which `Search.checkpoint` gathers and `Search.restore`
loads.
"""

from io       import BytesIO
from numpy    import ndarray
from pathlib  import Path
from pydantic import InstanceOf
from torch    import load, save
from typing   import Self

from squirtl.agent.checkpoint import archiving, reading
from squirtl.emulator.schemas import Record
from squirtl.search.schemas   import Frontier


class SearchCheckpoint(Record):
    """
    Everything a search holds at the end of an iteration, which `save`
    writes as one `.npz` holding its arrays beside a `frontier.json` member
    and a `networks.pt` member.
    """

    arrays: dict[str, InstanceOf[ndarray]]
    """
    Each array the tree and the predictor hold, under the name each gives it.
    """

    frontier: Frontier
    """
    The particles and the counters.
    """

    networks: dict[str, object]
    """
    What `Novelty.networks` gathers.
    """

    @classmethod
    def from_path(cls, path: Path) -> Self:
        """
        Reads the checkpoint `save` wrote at `path`. `torch.load` reads the
        networks onto the CPU under its default `weights_only=True`, which
        unpickles tensors and plain values alone.

        Raises:
            ValidationError : Where `frontier.json` holds no frontier.
            ValueError      : Where the file at `path` is cut short or
                              damaged, as `reading` raises.
        """
        members = {"frontier.json", "networks.pt"}

        with reading(path) as archive:
            return cls(
                arrays = {name: archive[name] for name in set(archive.files) - members},
                frontier = Frontier.model_validate_json(archive["frontier.json"]),
                networks = load(BytesIO(archive["networks.pt"]), map_location="cpu")
            )

    def save(self, path: Path):
        """
        Writes the checkpoint to `path` through `archiving`.
        """
        with archiving(self.arrays, path) as archive:
            with archive.open("frontier.json", "w") as member:
                member.write(self.frontier.model_dump_json().encode())

            with archive.open("networks.pt", "w") as member:
                save(self.networks, member)
