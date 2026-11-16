from __future__ import annotations

import struct
from dataclasses import dataclass

from henkan.errors import FormatError
from henkan.formats.sectors import SECTOR
from henkan.source import Source

MAGIC = b"MICROSOFT*XBOX*MEDIA"
BASES = (0, 0x0FD90000, 0x02080000, 0x18300000)
DESCRIPTOR_AT = 0x10000
SECOND_MAGIC_AT = 0x7EC
TABLE_MAX = 256 * 1024 * 1024
ENTRY_FIXED = 14
PADDING = 0xFFFF
UNIT = 4


@dataclass(frozen=True, slots=True)
class XdvdfsVolume:
    source: Source
    base: int
    sector: int
    size: int

    def names(self) -> tuple[str, ...]:
        if self.size > TABLE_MAX:
            raise FormatError(
                f"an XDVDFS directory of {self.size} bytes passes the limit of {TABLE_MAX}"
            )
        table = self.source.read(self.base + self.sector * SECTOR, self.size)
        return tuple(_names(table))


def _names(table: bytes) -> list[str]:
    names: list[str] = []
    seen: set[int] = set()
    pending = [0]
    while pending:
        offset = pending.pop()
        if offset in seen:
            continue
        seen.add(offset)
        if offset + ENTRY_FIXED > len(table):
            raise FormatError("an XDVDFS directory entry runs past its table")
        left, right = struct.unpack_from("<HH", table, offset)
        if left == PADDING and right == PADDING:
            continue
        name = table[offset + ENTRY_FIXED : offset + ENTRY_FIXED + table[offset + 13]]
        if len(name) != table[offset + 13]:
            raise FormatError("an XDVDFS directory entry runs past its table")
        names.append(name.decode("cp1252", errors="replace"))
        pending.extend(link * UNIT for link in (right, left) if link)
    return names


def read_volume(source: Source) -> XdvdfsVolume:
    for base in BASES:
        descriptor = source.peek(base + DESCRIPTOR_AT, SECTOR)
        if len(descriptor) < SECTOR or descriptor[: len(MAGIC)] != MAGIC:
            continue
        if descriptor[SECOND_MAGIC_AT : SECOND_MAGIC_AT + len(MAGIC)] != MAGIC:
            continue
        sector, size = struct.unpack_from("<II", descriptor, 0x14)
        return XdvdfsVolume(source, base, sector, size)
    raise FormatError(f"{source.name}: no XDVDFS volume")
