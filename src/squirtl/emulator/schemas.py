"""
Defines the records the emulator reads:

- `Record`, the base of a frozen record refusing a key no field declares
- `UnitInterval`, a float from 0 to 1, which the settings of each subject
  above the emulator bound a probability or a reward by
- `Button`, the buttons a step presses
- `Edition`, the releases of the game whose layout pret/pokered rebuilds
- `Symbol`, the addresses in the game's memory the package reads
- `Cartridge`, the ROM a run boots
- `EmulatorSettings`, the settings the emulator reads
"""

from enum      import IntEnum, StrEnum, auto
from functools import cached_property
from hashlib   import sha1
from pathlib   import Path
from pydantic  import BaseModel, Field, model_validator
from typing    import Annotated, Self

type UnitInterval = Annotated[float, Field(ge=0, le=1)]


class Button(StrEnum):
    """
    The buttons a step presses, meaning A, B, and the four directions, each
    member's value the name `PyBoy.button` takes for it.
    """

    A     = auto()
    B     = auto()
    DOWN  = auto()
    LEFT  = auto()
    RIGHT = auto()
    UP    = auto()


class Edition(StrEnum):
    """
    The English releases of Pokémon Red and Blue, whose memory layout the
    pret/pokered disassembly rebuilds, each member's value the SHA-1 digest
    its README lists for that release's ROM.
    """

    BLUE = "d7037c83e1ae5b39bde3c30787637ba1d4c48ce2"
    RED  = "ea9bcae617fdf159b045185467ae58b2e4a48b9a"


class Record(BaseModel, extra="forbid", frozen=True, use_attribute_docstrings=True):
    """
    The base of a frozen record, which refuses a key no field declares and
    an assignment once built, and takes the docstring beneath each field as
    that field's description.
    """


class Symbol(IntEnum):
    """
    The addresses in the game's memory the package reads, each member named
    for its label in pret/pokered's `ram/wram.asm` in SCREAMING_CASE, and
    its value the address the symbol files of both editions give that label:

    - `W_CUR_MAP`, the map the player stands on
    - `W_EVENT_FLAGS`, the first byte of the flag array recording each event
    - `W_X_COORD` and `W_Y_COORD`, the square of 2x2 tiles the player stands
      on in that map
    """

    W_CUR_MAP     = 0xD35E
    W_EVENT_FLAGS = 0xD747
    W_X_COORD     = 0xD362
    W_Y_COORD     = 0xD361


class Cartridge(Record):
    """
    The ROM a run boots, read from the file the user supplies and refused
    unless its SHA-1 digest is one `Edition` lists.
    """

    data: Annotated[bytes, Field(repr=False)]
    """
    The bytes of the ROM, which `GameBoy.boot` hands PyBoy in place of the
    path they were read from.
    """

    path: Path
    """
    The file the ROM was read from.
    """

    @cached_property
    def digest(self) -> str:
        """
        Hashes `data` through SHA-1.

        Returns:
            The digest as 40 lowercase hexadecimal digits, the form pret/pokered
            lists.
        """
        return sha1(self.data).hexdigest()

    @property
    def edition(self) -> Edition:
        """
        Names the release whose ROM the cartridge holds.
        """
        return Edition(self.digest)

    @classmethod
    def read(cls, path: Path) -> Self:
        """
        Reads the ROM in the file at `path`.

        Raises:
            FileNotFoundError : Where no file sits at `path`.
            ValidationError   : Where the file's digest names no release
                                `Edition` lists.
        """
        return cls(data=path.read_bytes(), path=path)

    @model_validator(mode="after")
    def verify(self) -> Self:
        """
        Refuses a ROM whose digest `Edition` does not list, naming the file
        it was read from.

        Raises:
            ValueError: Where the digest names no release `Edition` lists,
                        which Pydantic raises as a `ValidationError`.
        """
        if self.digest not in Edition:
            raise ValueError(
                f"{self.path} is not an English Pokémon Red or Blue ROM, since its "
                f"SHA-1 is {self.digest} where pret/pokered lists "
                f"{' or '.join(Edition)}"
            )

        return self


class EmulatorSettings(Record):
    """
    The settings the emulator reads, each a field of `RunSettings.emulator`
    and a key under `[tool.squirtl.emulator]` in `pyproject.toml`.
    """

    cartridge: Path = Path("data/rom.gb")
    """
    The file holding the user's own ROM of the English Pokémon Red or Blue,
    which a run refuses unless pret/pokered lists its SHA-1.
    """

    open_window: bool = False
    """
    Whether PyBoy draws the last frame of each step in an SDL2 window,
    pacing the steps at sixty a second, where otherwise a run draws nothing
    and advances as fast as the machine allows.
    """

    @property
    def window(self) -> str:
        """
        Names the window PyBoy draws the game in, meaning `SDL2` where
        `open_window` is set and otherwise `null`, which draws nothing.
        """
        return "SDL2" if self.open_window else "null"
