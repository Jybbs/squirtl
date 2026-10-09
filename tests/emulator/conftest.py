"""
Defines the fixtures the tests of `squirtl.emulator` share, meaning a
cartridge holding no game, written with a save beside it at the path a run
reads the user's own from, and the record of that cartridge.
"""

from pathlib import Path
from pytest  import fixture

from squirtl.emulator.schemas import Cartridge, EmulatorSettings


@fixture
def cartridge(rom: Path) -> Cartridge:
    """
    Builds the record of the cartridge `rom` writes without the check
    `Cartridge.read` runs, since pret/pokered lists no digest of that ROM.
    """
    return Cartridge.model_construct(data=rom.read_bytes(), path=rom)


@fixture
def rom(tmp_path: Path) -> Path:
    """
    Writes a 32 KiB cartridge holding no game under `tmp_path`, at the path
    `EmulatorSettings` reads by default, and beside it the save PyBoy reads
    for a cartridge at that path, which holds `0xAB` in each of its 32 KiB.

    The cartridge's entry point jumps to itself, and its header declares the
    MBC3 with battery-backed RAM that Pokémon Red and Blue use and carries
    the checksum Pan Docs gives, so PyBoy boots it and runs that one loop.
    """
    data              = bytearray(0x8000)
    data[0x100:0x102] = b"\x18\xfe"      # `jr @`, a relative jump back onto itself
    data[0x147:0x14A] = b"\x13\x00\x03"  # MBC3+RAM+BATTERY, 32 KiB of ROM and of RAM
    data[0x14D]       = -sum(byte + 1 for byte in data[0x134:0x14D]) % 256

    path = tmp_path / EmulatorSettings().cartridge
    path.parent.mkdir()
    path.write_bytes(data)
    Path(f"{path}.ram").write_bytes(b"\xab" * 0x8000)

    return path
