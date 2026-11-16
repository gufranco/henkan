from __future__ import annotations

import re

from henkan.errors import FormatError
from henkan.formats.sheet import TRACK_MAX, Sheet, Track, TrackType

LINE = re.compile(
    r'^(\d{1,4})\s+(\d{1,10})\s+(\d{1,4})\s+(\d{1,6})\s+(?:"([^"]+)"|(\S+))\s+(\d{1,12})$'
)
COUNT = re.compile(r"^\d{1,4}$")
KINDS = {
    (0, 2352): TrackType.AUDIO,
    (4, 2352): TrackType.MODE1_2352,
    (4, 2048): TrackType.MODE1_2048,
}


def _track(line: str) -> Track:
    match = LINE.match(line)
    if match is None:
        raise FormatError(f"GDI line {line!r} is not a track")
    number, stride = int(match[1]), int(match[4])
    if not 1 <= number <= TRACK_MAX:
        raise FormatError(f"GDI track {number} is outside 1 to {TRACK_MAX}")
    name = match[5] if match[5] is not None else match[6]
    kind = KINDS.get((int(match[3]), stride))
    return Track(number, kind, name, int(match[2]), stride, int(match[7]))


def parse(text: str) -> Sheet:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines or COUNT.match(lines[0]) is None:
        raise FormatError("not a GDI: its first line is not a track count")
    tracks = tuple(_track(line) for line in lines[1:])
    if not tracks:
        raise FormatError("not a GDI: it names no file")
    return Sheet(tuple(dict.fromkeys(track.file for track in tracks)), tracks)
