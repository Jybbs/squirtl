"""
Defines the file the agent writes at each checkpoint and reads back:

- `Checkpoint`, everything a resumed run continues training from, replay
  memory included
- `Weights`, the online network's weights and their step, which an
  evaluation reads from a checkpoint alone
"""

from compression.zstd import ZstdError
from io               import BytesIO
from numpy            import load as load_npz, ndarray, save as save_npy
from numpy.lib.npyio  import NpzFile
from os               import O_RDONLY, close, fsync, open as os_open
from pathlib          import Path
from pydantic         import InstanceOf, ValidatorFunctionWrapHandler, WrapValidator
from torch            import Tensor, load, save
from typing           import Annotated, Self
from zipfile          import BadZipFile, ZIP_ZSTANDARD, ZipFile

from squirtl.agent.schemas    import flush
from squirtl.emulator.schemas import Record

type StateDict = Annotated[
    dict[str, InstanceOf[Tensor]], WrapValidator(validate_in_place)
]


def validate_in_place(  # prose: ignore[unsorted-positionals]
    state   : object,
    handler : ValidatorFunctionWrapHandler
) -> object:
    """
    Validates each entry of `state` as a tensor through `handler`, then
    returns `state` itself, since the dict `handler` rebuilds drops the
    `_metadata` holding each module's version.
    """
    handler(state)

    return state


class Weights(Record, extra="ignore"):
    """
    The online network's weights and the step a checkpoint holds them at,
    which an evaluation reads from the checkpoint's `agent.pt` member alone.
    """

    online: StateDict
    """
    The online network's `state_dict`.
    """

    step: int
    """
    The environment steps the agent has remembered.
    """

    @classmethod
    def from_path(cls, path: Path) -> Self:
        """
        Reads the checkpoint `save` wrote at `path` through `members`, then
        validates each field the record declares.

        Raises:
            ValidationError : Where a field is missing or a network entry is
                              no tensor.
            ValueError      : Where the file at `path` is cut short or
                              damaged, in its zip directory, a zip header, a
                              zstd frame, or a member, naming `path`.
        """
        try:
            # `numpy.load` leaves a file it opened open where `ZipFile` refuses it.
            with path.open("rb") as file, load_npz(file) as archive:
                return cls.model_validate(cls.members(archive))
        except (
            BadZipFile, EOFError, KeyError, NotImplementedError, ZstdError
        ) as error:
            raise ValueError(f"{path} holds no whole checkpoint: {error}") from error

    @classmethod
    def members(cls, archive: NpzFile) -> dict[str, object]:
        """
        Reads the `agent.pt` member of `archive` onto the CPU, leaving
        replay memory's members unread. `torch.load` reads it under its
        default `weights_only=True`, which unpickles tensors and plain
        values alone.
        """
        return load(BytesIO(archive["agent.pt"]), map_location="cpu")


class Checkpoint(Weights, extra="forbid"):
    """
    Everything a resumed run continues training from, the `Weights` an
    evaluation reads among it, which `save` writes as one `.npz` holding
    replay memory's arrays beside an `agent.pt` member holding the rest.
    """

    exploration: dict[str, object]
    """
    The state of the generator choosing each random action.
    """

    optimizer: dict[str, object]
    """
    Adam's `state_dict`.
    """

    replay: dict[str, InstanceOf[ndarray]]
    """
    Each array replay memory holds, named as `Replay.arrays` names it.
    """

    sampling: dict[str, object]
    """
    The state of the generator drawing each batch from replay memory.
    """

    target: StateDict
    """
    The target network's `state_dict`.
    """

    @classmethod
    def members(cls, archive: NpzFile) -> dict[str, object]:
        """
        Reads `agent.pt` as `Weights.members` does and every other member of
        `archive` as an array of `replay`.
        """
        return super().members(archive) | {
            "replay":
                {name: archive[name] for name in archive.files if name != "agent.pt"}
        }

    def save(self, path: Path):
        """
        Writes the checkpoint to `path` as an `.npz` whose members `zipfile`
        compresses with zstd, an `.npy` member for each array of `replay`
        beside an `agent.pt` member. `torch.save` writes that member
        holding every other field as it is, so each `state_dict` keeps its
        `_metadata`.

        The archive is written to the `.partial` file beside `path` and
        flushed through the drive's own cache, then takes the name `path`,
        whose directory is flushed in turn. An interrupt therefore leaves
        the checkpoint at `path` as it was, and the `.partial` file goes
        whether or not the write raised.
        """
        partial = path.with_name(f"{path.name}.partial")

        try:
            with partial.open("wb") as file:
                with ZipFile(file, "w", ZIP_ZSTANDARD) as archive:
                    with archive.open("agent.pt", "w") as member:
                        save(
                            {key: value for key, value in self if key != "replay"},
                            member
                        )

                    for name, array in self.replay.items():
                        # ZIP64 lets the frames of a large replay memory pass 2 GiB.
                        with archive.open(
                            f"{name}.npy",
                            "w",
                            force_zip64 = True
                        ) as member:
                            save_npy(member, array)

                flush(file.fileno())

            partial.replace(path)
        finally:
            partial.unlink(missing_ok=True)

        directory = os_open(path.parent, O_RDONLY)

        try:
            fsync(directory)
        finally:
            close(directory)
