from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Entry:
    name: str
    directory: bool
    location: int
    size: int


class Volume(Protocol):
    def root(self) -> tuple[Entry, ...]: ...

    def children(self, entry: Entry) -> tuple[Entry, ...]: ...

    def read(self, entry: Entry, length: int) -> bytes: ...


def find(entries: Iterable[Entry], name: str) -> Entry | None:
    wanted = name.casefold()
    return next((entry for entry in entries if entry.name.casefold() == wanted), None)
