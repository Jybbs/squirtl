"""
Pins the records the emulator reads, covering:

- The cartridge a read refuses, naming its path, the one it reads as an
  edition, and the repr that leaves out its bytes
- The digest each edition holds and the address each symbol holds, against
  what pret/pokered publishes
"""

from hashlib  import sha1
from operator import attrgetter
from pathlib  import Path
from pydantic import ValidationError
from pytest   import MonkeyPatch, mark, raises
from re       import escape

from squirtl.emulator.schemas import Cartridge, Edition, EmulatorSettings, Symbol


def test_a_missing_cartridge_raises_naming_its_path(tmp_path: Path):
    """
    Asserts that reading a cartridge where no file sits raises an error
    naming the path a run looked in.
    """
    path = tmp_path / EmulatorSettings().cartridge

    with raises(FileNotFoundError, match=escape(str(path))):
        Cartridge.read(path)


def test_a_rom_pret_pokered_does_not_list_is_refused_naming_its_path(rom: Path):
    """
    Asserts that reading a ROM whose SHA-1 pret/pokered does not list raises
    an error naming the file, the digest it holds, and the digest of each
    release `Edition` lists.
    """
    with raises(
        ValidationError,
        match = escape(
            f"{rom} is not an English Pokémon Red or Blue ROM, since its SHA-1 is "
            f"{sha1(rom.read_bytes()).hexdigest()} where pret/pokered lists "
            f"{Edition.BLUE} or {Edition.RED}"
        )
    ):
        Cartridge.read(rom)


def test_each_edition_holds_the_digest_pret_pokered_lists():
    """
    Asserts that each edition holds the SHA-1 the pret/pokered README lists
    for that release's ROM, and that no other release reads as an edition.
    """
    assert {edition.name: edition.value for edition in Edition} == {
        "BLUE" : "d7037c83e1ae5b39bde3c30787637ba1d4c48ce2",
        "RED"  : "ea9bcae617fdf159b045185467ae58b2e4a48b9a"
    }


@mark.parametrize("edition", Edition, ids=attrgetter("name"))
def test_a_rom_pret_pokered_lists_reads_as_its_edition(
    edition     : Edition,
    monkeypatch : MonkeyPatch,
    rom         : Path
):
    """
    Asserts that a ROM whose digest pret/pokered lists reads as the edition
    that digest names, the digest standing in for the hash of a ROM no test
    may carry.
    """
    monkeypatch.setattr(Cartridge, "digest", edition.value)

    assert Cartridge.read(rom).edition is edition


def test_each_symbol_holds_the_address_pret_pokered_gives_its_label():
    """
    Asserts that each symbol holds the address that `pokered.sym` and
    `pokeblue.sym`, the symbol files pret/pokered publishes, both give its
    label.
    """
    assert {symbol.name: symbol.value for symbol in Symbol} == {
        "W_CUR_MAP"     : 0xD35E,
        "W_EVENT_FLAGS" : 0xD747,
        "W_X_COORD"     : 0xD362,
        "W_Y_COORD"     : 0xD361
    }


def test_the_repr_of_a_cartridge_names_its_path_and_leaves_out_its_bytes(
    cartridge: Cartridge
):
    """
    Asserts that the repr of a cartridge names the file it was read from and
    leaves out the ROM's bytes.
    """
    assert repr(cartridge) == f"Cartridge(path={cartridge.path!r})"
