from __future__ import annotations

import io
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from henkan.errors import FormatError
from henkan.limits import read_max


@dataclass(frozen=True, slots=True)
class Source:
    handle: BinaryIO
    size: int
    limit: int
    name: str

    def read(self, offset: int, length: int) -> bytes:
        if length > self.limit:
            raise FormatError(
                f"{self.name}: a read of {length} bytes passes the limit of {self.limit}"
            )
        if offset < 0 or length < 0 or offset + length > self.size:
            raise FormatError(
                f"{self.name}: {length} bytes at offset {offset} fall outside its {self.size} bytes"
            )
        self.handle.seek(offset)
        data = self.handle.read(length)
        if len(data) != length:
            raise FormatError(f"{self.name}: the file ended before {length} bytes at {offset}")
        return data

    def peek(self, offset: int, length: int) -> bytes:
        available = min(length, self.size - offset)
        if offset < 0 or available <= 0:
            return b""
        return self.read(offset, available)


def memory_source(data: bytes, *, name: str = "memory", limit: int | None = None) -> Source:
    return Source(io.BytesIO(data), len(data), read_max() if limit is None else limit, name)


@contextmanager
def open_source(path: Path, *, limit: int | None = None) -> Iterator[Source]:
    with path.open("rb") as handle:
        size = handle.seek(0, io.SEEK_END)
        yield Source(handle, size, read_max() if limit is None else limit, path.name)
