from __future__ import annotations

from henkan.errors import FormatError
from henkan.model import Format
from henkan.source import Source

MAGIC_AT = 0x100
CARD = b"NCSD"
EXECUTABLE = b"NCCH"
HOMEBREW = b"3DSX"
FIRST_PARTITION_AT = 0x120
MEDIA_UNIT = 0x200
FLAGS_AT = 0x18F
NO_CRYPTO = 0x04


def _decrypted(source: Source, base: int) -> bool:
    flags = source.peek(base + FLAGS_AT, 1)
    return bool(flags and flags[0] & NO_CRYPTO)


def _card(source: Source) -> tuple[Format, bool]:
    base = int.from_bytes(source.peek(FIRST_PARTITION_AT, 4), "little") * MEDIA_UNIT
    if source.peek(base + MAGIC_AT, 4) != EXECUTABLE:
        raise FormatError(f"{source.name}: a 3DS card image whose first partition is damaged")
    return Format.CCI, _decrypted(source, base)


def identify(source: Source) -> tuple[Format, bool] | None:
    if source.peek(0, 4) == HOMEBREW:
        return Format.HOMEBREW_3DS, True
    magic = source.peek(MAGIC_AT, 4)
    if magic == EXECUTABLE:
        return Format.CXI, _decrypted(source, 0)
    return _card(source) if magic == CARD else None
