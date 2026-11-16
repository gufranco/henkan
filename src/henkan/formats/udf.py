from __future__ import annotations

import struct
from collections.abc import Iterator
from dataclasses import dataclass

from henkan.errors import FormatError
from henkan.formats.sectors import SECTOR, SectorView
from henkan.formats.volume import Entry

RECOGNITION_SECTOR = 16
RECOGNITION_LIMIT = 16
RECOGNIZED = (b"NSR02", b"NSR03")
RECOGNITION_KNOWN = (b"BEA01", b"BOOT2", b"CD001", b"CDW02", b"TEA01")
ANCHOR_SECTOR = 256
SEQUENCE_LIMIT = 64
TAG_ANCHOR = 2
TAG_PARTITION = 5
TAG_LOGICAL_VOLUME = 6
TAG_TERMINATOR = 8
TAG_FILE_SET = 256
TAG_FILE_IDENTIFIER = 257
TAG_FILE_ENTRY = 261
TAG_EXTENDED_FILE_ENTRY = 266
TAG_SIZE = 16
PHYSICAL_MAP = 1
FILE_TYPE_DIRECTORY = 4
ALLOCATION_SHORT = 0
ALLOCATION_LONG = 1
ALLOCATION_EMBEDDED = 3
EXTENT_LENGTH_MASK = 0x3FFFFFFF
EXTENT_RECORDED = 0
IDENTIFIER_FIXED = 38
CHARACTERISTIC_DIRECTORY = 0x02
CHARACTERISTIC_DELETED = 0x04
CHARACTERISTIC_PARENT = 0x08
CHILDREN_MAX = 4096
DIRECTORY_MAX = 1024 * 1024
ENTRY_LAYOUT = {TAG_FILE_ENTRY: (168, 176), TAG_EXTENDED_FILE_ENTRY: (208, 216)}
DESCRIPTOR_SIZE = {ALLOCATION_SHORT: 8, ALLOCATION_LONG: 16}
ENCODINGS = {8: "latin-1", 16: "utf-16-be"}


@dataclass(frozen=True, slots=True)
class _Node:
    directory: bool
    length: int
    allocation: int
    descriptors: bytes


@dataclass(frozen=True, slots=True)
class UdfVolume:
    view: SectorView
    partition: int
    top: Entry
    label: str

    def root(self) -> tuple[Entry, ...]:
        return self.children(self.top)

    def children(self, entry: Entry) -> tuple[Entry, ...]:
        node = self._node(entry.location)
        if not node.directory:
            raise FormatError(f"{entry.name!r} is a file, not a directory")
        if node.length > DIRECTORY_MAX:
            raise FormatError(
                f"a directory of {node.length} bytes passes the limit of {DIRECTORY_MAX}"
            )
        found = tuple(_identifiers(self._data(node, node.length)))
        if len(found) > CHILDREN_MAX:
            raise FormatError(f"a directory holds more than {CHILDREN_MAX} entries")
        return tuple(self._entry(name, location) for name, location in found)

    def read(self, entry: Entry, length: int) -> bytes:
        node = self._node(entry.location)
        return self._data(node, min(length, node.length))

    def _entry(self, name: str, location: int) -> Entry:
        node = self._node(location)
        return Entry(name, node.directory, location, node.length)

    def _node(self, block: int) -> _Node:
        sector = self.view.sector(self.partition + block)
        tag = _tag(sector)
        if tag not in ENTRY_LAYOUT:
            raise FormatError(f"block {block} holds descriptor {tag}, not a file entry")
        lengths_at, data_at = ENTRY_LAYOUT[tag]
        (length,) = struct.unpack_from("<Q", sector, 56)
        attributes, descriptors = struct.unpack_from("<II", sector, lengths_at)
        start = data_at + attributes
        if start + descriptors > SECTOR:
            raise FormatError(f"the file entry at block {block} runs past its sector")
        (flags,) = struct.unpack_from("<H", sector, 34)
        directory = sector[27] == FILE_TYPE_DIRECTORY
        return _Node(directory, length, flags & 7, sector[start : start + descriptors])

    def _data(self, node: _Node, length: int) -> bytes:
        if node.allocation == ALLOCATION_EMBEDDED:
            return node.descriptors[:length]
        if node.allocation not in DESCRIPTOR_SIZE:
            raise FormatError(f"allocation type {node.allocation} is not one henkan reads")
        parts: list[bytes] = []
        wanted = length
        for extent, block in _extents(node):
            taken = min(wanted, extent)
            parts.append(self.view.read(self.partition + block, taken))
            wanted -= taken
        if wanted > 0:
            raise FormatError("a file's extents end before its recorded length")
        return b"".join(parts)


def _extents(node: _Node) -> Iterator[tuple[int, int]]:
    size = DESCRIPTOR_SIZE[node.allocation]
    for position in range(0, len(node.descriptors) - size + 1, size):
        raw, block = struct.unpack_from("<II", node.descriptors, position)
        if (
            node.allocation == ALLOCATION_LONG
            and node.descriptors[position + 8 : position + 10] != b"\0\0"
        ):
            raise FormatError("a file extent sits in a partition henkan does not read")
        if raw >> 30 != EXTENT_RECORDED:
            raise FormatError("a file extent is not recorded on the disc")
        yield raw & EXTENT_LENGTH_MASK, block


def _text(raw: bytes) -> str:
    if not raw or raw[0] not in ENCODINGS:
        raise FormatError("a file name uses a character encoding henkan does not read")
    return raw[1:].decode(ENCODINGS[raw[0]], errors="replace")


def _identifiers(data: bytes) -> Iterator[tuple[str, int]]:
    position = 0
    while position + IDENTIFIER_FIXED <= len(data):
        record = data[position:]
        if _tag(record) != TAG_FILE_IDENTIFIER:
            raise FormatError(f"a directory record at byte {position} is damaged")
        characteristics, name_length = record[18], record[19]
        (block, reference) = struct.unpack_from("<IH", record, 24)
        (use,) = struct.unpack_from("<H", record, 36)
        name = record[IDENTIFIER_FIXED + use : IDENTIFIER_FIXED + use + name_length]
        if len(name) != name_length or reference != 0:
            raise FormatError(f"a directory record at byte {position} is damaged")
        if not characteristics & (CHARACTERISTIC_DELETED | CHARACTERISTIC_PARENT):
            yield _text(name), block
        position += -(-(IDENTIFIER_FIXED + use + name_length) // 4) * 4


def _tag(descriptor: bytes) -> int:
    head = descriptor[:TAG_SIZE]
    if (sum(head) - head[4]) % 256 != head[4]:
        raise FormatError("a volume structure fails its checksum")
    identifier: int = struct.unpack_from("<H", head, 0)[0]
    return identifier


def _descriptor(view: SectorView, sector: int, expected: int) -> bytes:
    descriptor = view.sector(sector)
    tag = _tag(descriptor)
    if tag != expected:
        raise FormatError(f"sector {sector} holds descriptor {tag}, not {expected}")
    return descriptor


def _recognize(view: SectorView) -> None:
    for index in range(RECOGNITION_LIMIT):
        identifier = view.sector(RECOGNITION_SECTOR + index)[1:6]
        if identifier in RECOGNIZED:
            return
        if identifier not in RECOGNITION_KNOWN:
            break
    raise FormatError(f"{view.source.name}: no UDF volume recognition sequence")


def _sequence(view: SectorView, location: int, length: int) -> dict[int, bytes]:
    found: dict[int, bytes] = {}
    for index in range(min(length // SECTOR, SEQUENCE_LIMIT)):
        descriptor = view.sector(location + index)
        tag = _tag(descriptor)
        if tag == TAG_TERMINATOR:
            break
        found.setdefault(tag, descriptor)
    if TAG_PARTITION not in found or TAG_LOGICAL_VOLUME not in found:
        raise FormatError(f"{view.source.name}: the UDF volume names no partition")
    return found


def _file_set(logical: bytes, partition: bytes) -> int:
    (block_size,) = struct.unpack_from("<I", logical, 212)
    block, reference = struct.unpack_from("<IH", logical, 252)
    (maps,) = struct.unpack_from("<I", logical, 268)
    kind, _, _, number = struct.unpack_from("<BBHH", logical, 440)
    (declared,) = struct.unpack_from("<H", partition, 22)
    if block_size != SECTOR or maps < 1 or reference != 0 or kind != PHYSICAL_MAP:
        raise FormatError("the UDF volume uses a partition layout henkan does not read")
    if number != declared:
        raise FormatError("the UDF volume's partition map names a missing partition")
    return int(block)


def read_volume(view: SectorView) -> UdfVolume:
    _recognize(view)
    anchor = _descriptor(view, ANCHOR_SECTOR, TAG_ANCHOR)
    length, location = struct.unpack_from("<II", anchor, 16)
    found = _sequence(view, location, length)
    logical, partition = found[TAG_LOGICAL_VOLUME], found[TAG_PARTITION]
    (start,) = struct.unpack_from("<I", partition, 188)
    file_set = _descriptor(view, start + _file_set(logical, partition), TAG_FILE_SET)
    root, reference = struct.unpack_from("<IH", file_set, 404)
    if reference != 0:
        raise FormatError("the UDF root directory sits in a partition henkan does not read")
    label = logical[84:212]
    name = _text(label[: label[-1]]) if 0 < label[-1] < len(label) else ""
    return UdfVolume(view, start, Entry("", True, root, 0), name)
