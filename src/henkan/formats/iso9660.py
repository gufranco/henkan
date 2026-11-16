from __future__ import annotations

import struct
from collections.abc import Iterator
from dataclasses import dataclass

from henkan.errors import FormatError
from henkan.formats.sectors import SECTOR, SectorView
from henkan.formats.volume import Entry

DESCRIPTOR_SECTOR = 16
PRIMARY = 1
MAGIC = b"CD001"
ROOT_RECORD = 156
RECORD_MIN = 34
NAME_AT = 33
DIRECTORY_FLAG = 0x02
DIRECTORY_MAX = 1024 * 1024
SELF_AND_PARENT = (b"\x00", b"\x01")
LABEL = slice(40, 72)
VOLUME_SECTORS = 80


@dataclass(frozen=True, slots=True)
class IsoVolume:
    view: SectorView
    top: Entry
    sectors: int
    label: str

    def root(self) -> tuple[Entry, ...]:
        return self.children(self.top)

    def children(self, entry: Entry) -> tuple[Entry, ...]:
        if not entry.directory:
            raise FormatError(f"{entry.name!r} is a file, not a directory")
        if entry.size > DIRECTORY_MAX:
            raise FormatError(
                f"a directory of {entry.size} bytes passes the limit of {DIRECTORY_MAX}"
            )
        return tuple(_records(self.view.read(entry.location, entry.size)))

    def read(self, entry: Entry, length: int) -> bytes:
        return self.view.read(entry.location, min(length, entry.size))


def _name(raw: bytes) -> str:
    return raw.decode("latin-1").partition(";")[0].removesuffix(".")


def _record(record: bytes) -> Entry:
    location, size = struct.unpack_from("<I4xI", record, 2)
    name = record[NAME_AT : NAME_AT + record[32]]
    return Entry(_name(name), bool(record[25] & DIRECTORY_FLAG), location, size)


def _records(data: bytes) -> Iterator[Entry]:
    position = 0
    while position < len(data):
        length = data[position]
        if length == 0:
            position = (position // SECTOR + 1) * SECTOR
            continue
        record = data[position : position + length]
        if length < RECORD_MIN or len(record) < length or NAME_AT + record[32] > length:
            raise FormatError(f"a directory record at byte {position} is damaged")
        if record[NAME_AT : NAME_AT + record[32]] not in SELF_AND_PARENT:
            yield _record(record)
        position += length


def read_volume(view: SectorView) -> IsoVolume:
    descriptor = view.sector(DESCRIPTOR_SECTOR)
    if descriptor[0] != PRIMARY or descriptor[1:6] != MAGIC:
        raise FormatError(f"{view.source.name}: no ISO 9660 volume descriptor at sector 16")
    root = descriptor[ROOT_RECORD : ROOT_RECORD + RECORD_MIN]
    location, size = struct.unpack_from("<I4xI", root, 2)
    (sectors,) = struct.unpack_from("<I", descriptor, VOLUME_SECTORS)
    label = descriptor[LABEL].decode("latin-1").strip()
    return IsoVolume(view, Entry("", True, location, size), sectors, label)
