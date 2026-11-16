from __future__ import annotations

import re
from dataclasses import replace

from henkan.errors import FormatError
from henkan.formats.sectors import RAW_SECTOR
from henkan.formats.sheet import FRAMES_PER_SECOND, STRIDES, TRACK_MAX, Sheet, Track, TrackType

FILE = re.compile(r'^FILE\s+(?:"([^"]*)"|(\S+))', re.IGNORECASE)
TRACK = re.compile(r"^TRACK\s+(\d{1,4})\s+(\S+)", re.IGNORECASE)
INDEX = re.compile(r"^INDEX\s+(\d{1,4})\s+(\d{1,4}):(\d{1,4}):(\d{1,4})", re.IGNORECASE)
START_INDEX = 1
SECONDS_PER_MINUTE = 60
KINDS = {kind.value: kind for kind in TrackType}


def _file(match: re.Match[str]) -> str:
    name = match[1] if match[1] is not None else match[2]
    if not name:
        raise FormatError("a CUE FILE line names nothing")
    return name


def _track(match: re.Match[str], files: list[str]) -> Track:
    number = int(match[1])
    if not files:
        raise FormatError(f"CUE track {number} comes before any FILE")
    if not 1 <= number <= TRACK_MAX:
        raise FormatError(f"CUE track {number} is outside 1 to {TRACK_MAX}")
    kind = KINDS.get(match[2].upper())
    return Track(number, kind, files[-1], 0, STRIDES[kind] if kind else RAW_SECTOR, 0)


def _started(match: re.Match[str], tracks: list[Track]) -> Track:
    if not tracks:
        raise FormatError("a CUE INDEX comes before any TRACK")
    if int(match[1]) != START_INDEX:
        return tracks[-1]
    minutes, seconds, frames = int(match[2]), int(match[3]), int(match[4])
    if seconds >= SECONDS_PER_MINUTE or frames >= FRAMES_PER_SECOND:
        raise FormatError(f"CUE position {match[2]}:{match[3]}:{match[4]} is not a time")
    start = (minutes * SECONDS_PER_MINUTE + seconds) * FRAMES_PER_SECOND + frames
    return replace(tracks[-1], start=start, offset=start * tracks[-1].stride)


def parse(text: str) -> Sheet:
    files: list[str] = []
    tracks: list[Track] = []
    for line in text.splitlines():
        stripped = line.strip()
        if match := FILE.match(stripped):
            files.append(_file(match))
        elif match := TRACK.match(stripped):
            tracks.append(_track(match, files))
        elif match := INDEX.match(stripped):
            tracks[-1:] = [_started(match, tracks)]
    if not files:
        raise FormatError("not a CUE sheet: it names no file")
    return Sheet(tuple(dict.fromkeys(files)), tuple(tracks))
