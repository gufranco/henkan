from __future__ import annotations

import struct

from henkan.errors import FormatError

MAGIC = b"\0PSF"
HEADER_SIZE = 20
ENTRY_SIZE = 16
ENTRIES_MAX = 512
SIZE_MAX = 1024 * 1024
INTEGER = 0x0404
KEY_MAX = 64


def _entry(data: bytes, keys_at: int, values_at: int, index: int) -> tuple[str, str | int]:
    at = HEADER_SIZE + ENTRY_SIZE * index
    raw = data[at : at + ENTRY_SIZE]
    if len(raw) < ENTRY_SIZE:
        raise FormatError(f"PARAM.SFO entry {index} is cut short")
    key_at, kind, used, _, value_at = struct.unpack("<HHIII", raw)
    key = data[keys_at + key_at : keys_at + key_at + KEY_MAX].partition(b"\0")[0]
    value = data[values_at + value_at : values_at + value_at + used]
    name = key.decode("ascii", errors="replace")
    if kind != INTEGER:
        return name, value.partition(b"\0")[0].decode("utf-8", errors="replace")
    if len(value) < 4:
        raise FormatError(f"PARAM.SFO entry {index} holds a number that is cut short")
    return name, int.from_bytes(value[:4], "little")


def parse(data: bytes) -> dict[str, str | int]:
    if len(data) < HEADER_SIZE or data[:4] != MAGIC:
        raise FormatError("not a PARAM.SFO")
    keys_at, values_at, count = struct.unpack_from("<III", data, 8)
    if count > ENTRIES_MAX:
        raise FormatError(f"a PARAM.SFO with {count} entries passes the limit of {ENTRIES_MAX}")
    return dict(_entry(data, keys_at, values_at, index) for index in range(count))


def text(values: dict[str, str | int], key: str) -> str:
    value = values.get(key, "")
    return value if isinstance(value, str) else ""
