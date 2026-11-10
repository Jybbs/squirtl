"""
Defines the file the agents write at each checkpoint and read back:

- `Checkpoint`, everything a resumed run continues training from, whose
  `ReplayCheckpoint` holds replay memory for the deep Q-network and whose
  `RolloutCheckpoint` holds the generator of PQN or PPO
- `Weights`, the weights of the network an agent acts through and their
  step, which an evaluation reads from a checkpoint alone and a release
  carries as a checkpoint of its own
"""

from compression.zstd import ZstdError
from io               import BytesIO
from numpy            import load as load_npz, ndarray, save as save_npy
from numpy.lib.npyio  import NpzFile
from os               import O_RDONLY, close, fsync, open as os_open
from pathlib          import Path
from pydantic         import InstanceOf, ValidatorFunctionWrapHandler, WrapValidator
from torch            import Tensor, load, save
from torch.serialization import safe_globals
from typing              import Annotated, Self
from zipfile             import BadZipFile, ZIP_ZSTANDARD, ZipFile, ZipInfo

from squirtl.agent.schemas    import flush
from squirtl.emulator.schemas import Record

type StateDict = Annotated[
    dict[str, InstanceOf[Tensor]], WrapValidator(validate_in_place)
]


def member(name: str) -> ZipInfo:
    """
    Names a member of an archive `zipfile` compresses with zstd, dated
    1980-01-01, the earliest date a zip header holds and `ZipInfo`'s
    default, in place of the time it is written.
    """
    entry               = ZipInfo(name)
    entry.compress_type = ZIP_ZSTANDARD

    return entry


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
    The weights of the network an agent acts through and the step
    a checkpoint holds them at, which an evaluation reads from the
    checkpoint's `agent.pt` member alone and `save` writes as a checkpoint
    holding nothing else.
    """

    online: StateDict
    """
    The `state_dict` of the network the agent acts through, the online
    network for the deep Q-network.
    """

    step: int
    """
    The environment steps the agent has taken.
    """

    @property
    def arrays(self) -> dict[str, ndarray]:
        """
        Lists each array `save` writes as an `.npy` member of its own, none
        beyond what `agent.pt` holds.
        """
        return {}

    @property
    def contents(self) -> dict[str, object]:
        """
        Gathers what the `agent.pt` member holds, every field as it is, so
        each `state_dict` keeps its `_metadata`.
        """
        return dict(self)

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
            # `numpy.load` leaves a file it opened itself open where `ZipFile` refuses
            # it, so the file is opened here and closed by this block.
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
        every other member unread. `torch.load` reads it under its default
        `weights_only=True`, which unpickles tensors and plain values alone,
        with the `bytes` global allowed for the recording of an episode no
        step has played, since `torch.save` pickles an empty `bytes` through
        that global.
        """
        with safe_globals([bytes]):
            return load(BytesIO(archive["agent.pt"]), map_location="cpu")

    def save(self, path: Path):
        """
        Writes the checkpoint to `path` as an `.npz` whose members `zipfile`
        compresses with zstd, an `agent.pt` member that `torch.save` writes
        from `contents` beside an `.npy` member for each of `arrays`, each
        member dated as `member` dates it, so the same fields always write
        the same bytes.

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
                    with archive.open(member("agent.pt"), "w") as written:
                        save(self.contents, written)

                    for name, array in self.arrays.items():
                        # ZIP64 lets the frames of a large replay memory pass 2 GiB.
                        with archive.open(
                            member(f"{name}.npy"),
                            "w",
                            force_zip64 = True
                        ) as written:
                            save_npy(written, array)

                flush(file.fileno())

            partial.replace(path)
        finally:
            partial.unlink(missing_ok=True)

        directory = os_open(path.parent, O_RDONLY)

        try:
            fsync(directory)
        finally:
            close(directory)


class Checkpoint(Weights, extra="forbid"):
    """
    Everything a resumed run continues training from, the `Weights` an
    evaluation reads among it, which `save` writes as one `.npz` holding an
    `agent.pt` member beside an `.npy` member for each of its `arrays`.
    """

    optimizer: dict[str, object]
    """
    The optimizer's `state_dict`.
    """


class ReplayCheckpoint(Checkpoint):
    """
    Everything a resumed run of the deep Q-network continues training from,
    replay memory's arrays written as members of their own.
    """

    exploration: dict[str, object]
    """
    The state of the generator choosing each random action.
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

    @property
    def arrays(self) -> dict[str, ndarray]:
        """
        Lists replay memory's arrays.
        """
        return self.replay

    @property
    def contents(self) -> dict[str, object]:
        """
        Gathers every field but `replay`, as `Checkpoint.contents` does.
        """
        return {
            key: value for key, value in super().contents.items() if key != "replay"
        }

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


class RolloutCheckpoint(Checkpoint):
    """
    Everything a resumed run of PQN or PPO continues training from on the
    agent's side.
    """

    generator: dict[str, object]
    """
    The state of the generator every random draw of the agent comes from.
    """
