from __future__ import annotations

import struct

from henkan.errors import FormatError
from henkan.formats.sheet import TRACK_MAX, Sheet, Track, TrackType
from henkan.source import Source

MAGIC = b"MEDIA DESCRIPTOR"
VERSION = 1
HEADER_SIZE = 0x58
SESSION_SIZE = 24
BLOCK_SIZE = 0x50
AUDIO_MODE = 0xA9
STRIDES = (2048, 2336, 2352, 2368, 2448)
NAME_MAX = 520
EXTENSIONS = (".mdf", ".img")
PATTERN_PREFIX = "*"


def _name(source: Source, footer_at: int) -> str:
    name_at, wide = struct.unpack("<II", source.read(footer_at, 8))
    raw = source.peek(name_at, NAME_MAX)
    text = raw.decode("utf-16-le" if wide else "latin-1", errors="replace")
    name = text.partition("\0")[0]
    if not name:
        raise FormatError(f"{source.name}: the MDS names no data file")
    return name


def _track(source: Source, block: bytes) -> tuple[Track, int]:
    point = block[4]
    (stride,) = struct.unpack_from("<H", block, 0x10)
    start, offset, files, footer_at = struct.unpack_from("<IQII", block, 0x24)
    if files != 1:
        raise FormatError(
            f"{source.name}: track {point} spans {files} data files; henkan reads one"
        )
    if stride not in STRIDES:
        raise FormatError(
            f"{source.name}: track {point} has {stride}-byte sectors, which henkan does not read"
        )
    kind = TrackType.AUDIO if block[0] == AUDIO_MODE else None
    return Track(point, kind, "", start, stride, offset), footer_at


def _blocks(source: Source) -> tuple[int, int]:
    head = source.read(0, HEADER_SIZE)
    if head[: len(MAGIC)] != MAGIC:
        raise FormatError(f"{source.name}: not an MDS descriptor")
    if head[16] != VERSION:
        raise FormatError(f"{source.name}: MDS version {head[16]} is not one henkan reads")
    (sessions,) = struct.unpack_from("<H", head, 0x14)
    if sessions != 1:
        raise FormatError(f"{source.name}: an MDS with {sessions} sessions; henkan reads one")
    (session_at,) = struct.unpack_from("<I", head, 0x50)
    session = struct.unpack("<iiHBBHHII", source.read(session_at, SESSION_SIZE))
    return session[3], session[8]


def candidates(recorded: str, stem: str) -> tuple[str, ...]:
    if recorded.startswith(PATTERN_PREFIX):
        named = stem + recorded.removeprefix(PATTERN_PREFIX)
    else:
        named = recorded.replace("\\", "/").rpartition("/")[2]
    names = (named, *(stem + extension for extension in EXTENSIONS))
    return tuple(dict.fromkeys(name for name in names if name))


def parse(source: Source) -> Sheet:
    count, blocks_at = _blocks(source)
    raw = (source.read(blocks_at + index * BLOCK_SIZE, BLOCK_SIZE) for index in range(count))
    found = [_track(source, block) for block in raw if 1 <= block[4] <= TRACK_MAX]
    if not found:
        raise FormatError(f"{source.name}: an MDS with no tracks")
    name = _name(source, found[0][1])
    tracks = sorted((track for track, _ in found), key=lambda track: track.number)
    return Sheet(
        (name,), tuple(Track(t.number, t.kind, name, t.start, t.stride, t.offset) for t in tracks)
    )
