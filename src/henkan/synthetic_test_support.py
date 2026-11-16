from __future__ import annotations

import struct
from collections.abc import Mapping
from dataclasses import dataclass

from henkan.formats.sectors import RAW_SECTOR, SECTOR, SYNC

ISO_FIRST_FREE = 18
UDF_PARTITION = 272
UDF_SEQUENCE = 32
UDF_ANCHOR = 256

type Tree = Mapping[str, bytes | Tree]


def patched(image: bytes, offset: int, data: bytes) -> bytes:
    return image[:offset] + data + image[offset + len(data) :]


def _sectors(data: bytes) -> bytes:
    return data + bytes(-len(data) % SECTOR)


def _both(value: int) -> bytes:
    return struct.pack("<I", value) + struct.pack(">I", value)


def iso_record(name: bytes, sector: int, size: int, *, directory: bool) -> bytes:
    body = (
        b"\0"
        + _both(sector)
        + _both(size)
        + bytes(7)
        + bytes((2 if directory else 0, 0, 0))
        + struct.pack("<H", 1)
        + struct.pack(">H", 1)
        + bytes((len(name),))
        + name
    )
    padded = body + bytes(len(body) % 2 == 0)
    return bytes((len(padded) + 1,)) + padded


def _iso_directory(records: list[bytes]) -> bytes:
    data = b""
    for record in records:
        if len(data) % SECTOR + len(record) > SECTOR:
            data = _sectors(data)
        data += record
    return _sectors(data)


def _iso_place(image: bytearray, tree: Tree, parent: int | None) -> tuple[int, int]:
    names = [name.encode("latin-1") for name in tree]
    blanks = [iso_record(name, 0, 0, directory=False) for name in (b"\0", b"\1", *names)]
    sector, size = len(image) // SECTOR, len(_iso_directory(blanks))
    image += bytes(size)
    records = [
        iso_record(b"\0", sector, size, directory=True),
        iso_record(b"\1", sector if parent is None else parent, size, directory=True),
    ]
    for name, content in tree.items():
        if isinstance(content, bytes):
            records.append(
                iso_record(
                    name.encode("latin-1"), len(image) // SECTOR, len(content), directory=False
                )
            )
            image += _sectors(content)
        else:
            where, length = _iso_place(image, content, sector)
            records.append(iso_record(name.encode("latin-1"), where, length, directory=True))
    image[sector * SECTOR : sector * SECTOR + size] = _iso_directory(records)
    return sector, size


def iso_image(tree: Tree, *, label: str = "") -> bytes:
    image = bytearray(ISO_FIRST_FREE * SECTOR)
    sector, size = _iso_place(image, tree, None)
    descriptor = bytearray(SECTOR)
    descriptor[0:7] = b"\x01CD001\x01"
    descriptor[40:72] = label.encode("latin-1").ljust(32)
    descriptor[80:88] = _both(len(image) // SECTOR)
    descriptor[156:190] = iso_record(b"\0", sector, size, directory=True)
    image[16 * SECTOR : 17 * SECTOR] = descriptor
    image[17 * SECTOR : 17 * SECTOR + 7] = b"\xffCD001\x01"
    return bytes(image)


def bcd(value: int) -> int:
    return value // 10 * 16 + value % 10


def raw_image(data: bytes, mode: int) -> bytes:
    sectors = []
    for index in range(len(data) // SECTOR):
        frame = index + 150
        address = bytes((bcd(frame // 4500), bcd(frame // 75 % 60), bcd(frame % 75), mode))
        subheader = bytes(8) if mode == 2 else b""
        body = SYNC + address + subheader + data[index * SECTOR : (index + 1) * SECTOR]
        sectors.append(body.ljust(RAW_SECTOR, b"\0"))
    return b"".join(sectors)


def udf_tag(identifier: int, body: bytes, *, size: int = SECTOR) -> bytes:
    head = bytearray(struct.pack("<HHBBHHHI", identifier, 2, 0, 0, 0, 0, 0, 0))
    head[4] = sum(head) % 256
    return (bytes(head) + body).ljust(size, b"\0")


def _long_address(block: int) -> bytes:
    return struct.pack("<IIH6x", SECTOR, block, 0)


def udf_identifier(name: str, block: int, *, characteristics: int = 0) -> bytes:
    wide = any(ord(character) > 255 for character in name)
    encoded = (b"\x10" + name.encode("utf-16-be")) if wide else (b"\x08" + name.encode("latin-1"))
    text = encoded if name else b""
    body = struct.pack("<HBB", 1, characteristics, len(text)) + _long_address(block) + bytes(2)
    record = udf_tag(257, body + text, size=0)
    return record + bytes(-len(record) % 4)


@dataclass(frozen=True, slots=True)
class UdfOptions:
    extended: bool = False
    allocation: int = 0


def _udf_entry(directory: bool, length: int, descriptors: bytes, options: UdfOptions) -> bytes:
    fixed = 216 if options.extended else 176
    body = bytearray(fixed - 16)
    body[27 - 16] = 4 if directory else 5
    body[34 - 16 : 36 - 16] = struct.pack("<H", options.allocation)
    body[56 - 16 : 64 - 16] = struct.pack("<Q", length)
    body[fixed - 20 : fixed - 16] = struct.pack("<I", len(descriptors))
    return udf_tag(266 if options.extended else 261, bytes(body) + descriptors)


def _udf_store(blocks: list[bytes], data: bytes, options: UdfOptions) -> bytes:
    if options.allocation == 3:
        return data
    first = len(blocks)
    blocks.extend(_sectors(data)[at : at + SECTOR] for at in range(0, len(data), SECTOR))
    if options.allocation == 1:
        return struct.pack("<II8x", len(data), first)
    return struct.pack("<II", len(data), first)


def _udf_place(blocks: list[bytes], tree: Tree, options: UdfOptions) -> int:
    block = len(blocks)
    blocks.append(b"")
    records = [udf_identifier("", block, characteristics=0x0A)]
    for name, content in tree.items():
        if isinstance(content, bytes):
            child = len(blocks)
            blocks.append(b"")
            descriptors = _udf_store(blocks, content, options)
            blocks[child] = _udf_entry(False, len(content), descriptors, options)
            records.append(udf_identifier(name, child))
        else:
            where = _udf_place(blocks, content, options)
            records.append(udf_identifier(name, where, characteristics=0x02))
    data = b"".join(records)
    blocks[block] = _udf_entry(True, len(data), _udf_store(blocks, data, options), options)
    return block


def udf_image(tree: Tree, *, label: str = "", options: UdfOptions | None = None) -> bytes:
    blocks: list[bytes] = [b""]
    root = _udf_place(blocks, tree, options or UdfOptions())
    blocks[0] = udf_tag(256, bytes(384) + _long_address(root))
    image = bytearray(UDF_PARTITION * SECTOR) + b"".join(blocks)
    for index, name in enumerate((b"BEA01", b"NSR02", b"TEA01")):
        image[(16 + index) * SECTOR : (16 + index) * SECTOR + 7] = b"\0" + name + b"\x01"
    partition = bytearray(SECTOR - 16)
    partition[188 - 16 : 196 - 16] = struct.pack("<II", UDF_PARTITION, len(blocks))
    text = (b"\x08" + label.encode("latin-1")) if label else b""
    logical = bytearray(SECTOR - 16)
    logical[84 - 16 : 212 - 16] = text.ljust(127, b"\0") + bytes((len(text),))
    logical[212 - 16 : 216 - 16] = struct.pack("<I", SECTOR)
    logical[248 - 16 : 264 - 16] = _long_address(0)
    logical[264 - 16 : 272 - 16] = struct.pack("<II", 6, 1)
    logical[440 - 16 : 446 - 16] = struct.pack("<BBHH", 1, 6, 1, 0)
    sequence = (udf_tag(5, bytes(partition)), udf_tag(6, bytes(logical)), udf_tag(8, b""))
    image[UDF_SEQUENCE * SECTOR : (UDF_SEQUENCE + 3) * SECTOR] = b"".join(sequence)
    anchor = udf_tag(2, struct.pack("<II", 3 * SECTOR, UDF_SEQUENCE))
    image[UDF_ANCHOR * SECTOR : (UDF_ANCHOR + 1) * SECTOR] = anchor
    return bytes(image)


@dataclass(frozen=True, slots=True)
class MdsTrack:
    mode: int
    point: int
    stride: int
    start: int
    offset: int
    files: int = 1


def mds_image(tracks: tuple[MdsTrack, ...], name: str, *, wide: bool = False) -> bytes:
    blocks_at = 0x70
    footer_at = blocks_at + 0x50 * len(tracks)
    head = bytearray(0x58)
    head[0:17] = b"MEDIA DESCRIPTOR\x01"
    head[0x14:0x16] = struct.pack("<H", 1)
    head[0x50:0x54] = struct.pack("<I", 0x58)
    session = struct.pack("<iiHBBHHII", -150, 0, 1, len(tracks), 0, 1, 1, 0, blocks_at)
    blocks = bytearray()
    for track in tracks:
        block = bytearray(0x50)
        block[0], block[4] = track.mode, track.point
        block[0x10:0x12] = struct.pack("<H", track.stride)
        block[0x24:0x38] = struct.pack("<IQII", track.start, track.offset, track.files, footer_at)
        blocks += block
    text = name.encode("utf-16-le" if wide else "latin-1") + bytes(2)
    footer = struct.pack("<II", footer_at + 8, int(wide))
    return bytes(head) + session + bytes(blocks) + footer + text
