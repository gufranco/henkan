from __future__ import annotations

from dataclasses import dataclass

from henkan.errors import FormatError
from henkan.source import Source

SECTOR = 2048
RAW_SECTOR = 2352
SYNC = bytes((0, *(0xFF,) * 10, 0))
MODE_BYTE = 15
RAW_MODES = (1, 2)


@dataclass(frozen=True, slots=True)
class Layout:
    stride: int
    offset: int


COOKED = Layout(SECTOR, 0)
RAW_MODE1 = Layout(RAW_SECTOR, 16)
RAW_MODE2 = Layout(RAW_SECTOR, 24)
LAYOUTS = (COOKED, RAW_MODE1, RAW_MODE2)


@dataclass(frozen=True, slots=True)
class SectorView:
    source: Source
    layout: Layout
    base: int = 0

    def sector(self, number: int) -> bytes:
        if number < 0:
            raise FormatError(f"{self.source.name}: sector {number} does not exist")
        position = self.base + number * self.layout.stride + self.layout.offset
        return self.source.read(position, SECTOR)

    def read(self, number: int, length: int) -> bytes:
        if length < 0 or length > self.source.limit:
            raise FormatError(
                f"{self.source.name}: a read of {length} bytes passes the limit of "
                f"{self.source.limit}"
            )
        whole = -(-length // SECTOR)
        data = b"".join(self.sector(number + index) for index in range(whole))
        return data[:length]


def raw_mode(source: Source, base: int = 0) -> int | None:
    head = source.peek(base, MODE_BYTE + 1)
    if len(head) <= MODE_BYTE or head[: len(SYNC)] != SYNC or head[MODE_BYTE] not in RAW_MODES:
        return None
    return head[MODE_BYTE]
