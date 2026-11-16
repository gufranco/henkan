from __future__ import annotations

import random
import struct
from collections.abc import Mapping
from dataclasses import dataclass

from henkan.formats.sectors import RAW_SECTOR, SECTOR, SYNC

SEED = 20261116
ISO_FIRST_FREE = 18
UDF_PARTITION = 272
UDF_SEQUENCE = 32
UDF_ANCHOR = 256

type Tree = Mapping[str, bytes | Tree]


def rng() -> random.Random:
    return random.Random(SEED)  # noqa: S311


def game_code(source: random.Random) -> tuple[str, str]:
    letters = "".join(source.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=4))
    digits = "".join(source.choices("0123456789", k=5))
    return letters, digits


def title(source: random.Random) -> str:
    words = ("Lantern", "Harbor", "Circuit", "Meadow", "Comet", "Atlas", "Ember", "Tide")
    return " ".join(source.sample(words, k=3))


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


def sfo(values: Mapping[str, str | int]) -> bytes:
    keys, data, entries = b"", b"", b""
    for key, value in values.items():
        raw = struct.pack("<I", value) if isinstance(value, int) else value.encode() + b"\0"
        kind = 0x0404 if isinstance(value, int) else 0x0204
        entries += struct.pack("<HHIII", len(keys), kind, len(raw), len(raw), len(data))
        keys += key.encode() + b"\0"
        data += raw
    keys_at = 20 + len(entries)
    head = b"\0PSF" + struct.pack("<IIII", 0x101, keys_at, keys_at + len(keys), len(values))
    return head + entries + keys + data


def xdvdfs_volume(names: tuple[str, ...]) -> bytes:
    table = bytearray(b"\xff" * SECTOR)
    position = 0
    for index, name in enumerate(sorted(names, key=str.upper)):
        raw = name.encode("cp1252")
        size = -(-(14 + len(raw)) // 4) * 4
        following = (position + size) // 4 if index + 1 < len(names) else 0
        entry = struct.pack("<HHIIBB", 0, following, 40 + index, 0, 0x80, len(raw)) + raw
        table[position : position + len(entry)] = entry
        position += size
    descriptor = bytearray(SECTOR)
    descriptor[0:20] = descriptor[0x7EC:0x800] = b"MICROSOFT*XBOX*MEDIA"
    descriptor[0x14:0x1C] = struct.pack("<II", 33, SECTOR)
    return bytes(0x10000) + bytes(descriptor) + bytes(table)


def pbp_image(discs: int, values: Mapping[str, str | int]) -> bytes:
    param = sfo(values)
    psar_at = 0x10000
    offsets = (0x28, *((0x28 + len(param),) * 6), psar_at)
    head = b"\0PBP" + struct.pack("<I8I", 0x10000, *offsets) + param
    if discs == 1:
        return head.ljust(psar_at, b"\0") + b"PSISOIMG0000" + bytes(0x400)
    table = struct.pack(
        "<5I", *(0x8000 * (index + 1) if index < discs else 0 for index in range(5))
    )
    return head.ljust(psar_at, b"\0") + b"PSTITLEIMG000000".ljust(0x200, b"\0") + table


def nintendo_header(code: str, name: str, *, wii: bool) -> bytes:
    head = bytearray(0x60)
    head[0:6] = code.encode()
    head[0x18:0x20] = bytes.fromhex("5D1C9EA300000000" if wii else "00000000C2339F3D")
    head[0x20 : 0x20 + len(name)] = name.encode()
    return bytes(head)


def npdm(title_id: int, acid_gap: int) -> bytes:
    data = bytearray(0x700)
    data[0:4] = b"META"
    data[0x70:0x7C] = struct.pack("<III", 0x80, 0x60, 0x100)
    data[0x80:0x84] = b"ACI0"
    data[0x90:0x98] = struct.pack("<Q", title_id)
    data[0x100 + acid_gap : 0x104 + acid_gap] = b"ACID"
    return bytes(data)


def ncch(*, decrypted: bool) -> bytes:
    data = bytearray(0x200)
    data[0x100:0x104] = b"NCCH"
    data[0x18F] = 4 if decrypted else 0
    return bytes(data)


def ncsd(partition: bytes) -> bytes:
    data = bytearray(0x4000)
    data[0x100:0x104] = b"NCSD"
    data[0x120:0x128] = struct.pack("<II", 0x20, len(partition) // 0x200)
    return bytes(data) + partition
