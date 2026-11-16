from __future__ import annotations

import struct
from dataclasses import dataclass

from henkan.errors import FormatError
from henkan.formats import sfo
from henkan.source import Source

MAGIC = b"\0PBP"
HEADER_SIZE = 40
SINGLE = b"PSISOIMG0000"
MULTI = b"PSTITLEIMG000000"
DISC_TABLE_AT = 0x200
DISC_SLOTS = 5


@dataclass(frozen=True, slots=True)
class Pbp:
    discs: int
    disc_id: str


def _discs(source: Source, psar: int) -> int:
    magic = source.peek(psar, len(MULTI))
    if magic.startswith(SINGLE):
        return 1
    if magic != MULTI:
        raise FormatError(f"{source.name}: a PBP that holds no PS1 game")
    slots = struct.unpack(f"<{DISC_SLOTS}I", source.read(psar + DISC_TABLE_AT, 4 * DISC_SLOTS))
    used = sum(1 for slot in slots if slot)
    if used == 0:
        raise FormatError(f"{source.name}: a multi-disc PBP that lists no disc")
    return used


def read(source: Source) -> Pbp:
    head = source.peek(0, HEADER_SIZE)
    if len(head) < HEADER_SIZE or head[:4] != MAGIC:
        raise FormatError(f"{source.name}: not a PBP")
    offsets = struct.unpack_from("<8I", head, 8)
    param, following, psar = offsets[0], offsets[1], offsets[7]
    if not 0 <= following - param <= sfo.SIZE_MAX:
        raise FormatError(f"{source.name}: the PBP header is damaged")
    values = sfo.parse(source.read(param, following - param))
    return Pbp(_discs(source, psar), sfo.text(values, "DISC_ID").upper())
