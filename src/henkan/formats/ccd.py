from __future__ import annotations

import re

from henkan.errors import FormatError
from henkan.formats.sectors import RAW_SECTOR
from henkan.formats.sheet import TRACK_MAX, Sheet, Track, TrackType

SECTION = re.compile(r"^\[([^\]]{1,64})\]$")
NUMBER = re.compile(r"^(-?)(?:0x([0-9a-f]{1,8})|(\d{1,10}))$", re.IGNORECASE)
TRACK_SECTION = re.compile(r"^track (\d{1,4})$")
ENTRY_SECTION = re.compile(r"^entry \d{1,4}$")
DATA_CONTROL = 0x04
MODES = {0: TrackType.AUDIO, 1: TrackType.MODE1_2352, 2: TrackType.MODE2_2352}

type Section = tuple[str, dict[str, str]]


def _sections(text: str) -> list[Section]:
    sections: list[Section] = []
    for line in text.splitlines():
        stripped = line.strip()
        if match := SECTION.match(stripped):
            sections.append((match[1].casefold(), {}))
        elif sections and "=" in stripped:
            key, _, value = stripped.partition("=")
            sections[-1][1][key.strip().casefold()] = value.strip()
    return sections


def _number(value: str) -> int:
    match = NUMBER.match(value)
    if match is None:
        raise FormatError(f"CCD value {value!r} is not a number")
    magnitude = int(match[2], 16) if match[2] else int(match[3])
    return -magnitude if match[1] else magnitude


def _track(number: int, kind: TrackType | None, start: str | None, image: str) -> Track:
    if not 1 <= number <= TRACK_MAX:
        raise FormatError(f"CCD track {number} is outside 1 to {TRACK_MAX}")
    if start is None:
        raise FormatError(f"CCD track {number} has no mode or no start")
    sector = _number(start)
    if sector < 0:
        raise FormatError(f"CCD track {number} starts before the disc")
    return Track(number, kind, image, sector, RAW_SECTOR, sector * RAW_SECTOR)


def _from_tracks(sections: list[Section], image: str) -> list[Track]:
    tracks: list[Track] = []
    for name, values in sections:
        match = TRACK_SECTION.match(name)
        if match is None:
            continue
        start = values.get("index 1") if "mode" in values else None
        kind = MODES.get(_number(values["mode"])) if "mode" in values else None
        tracks.append(_track(int(match[1]), kind, start, image))
    return tracks


def _from_entries(sections: list[Section], image: str) -> list[Track]:
    tracks: list[Track] = []
    for name, values in sections:
        point = _number(values.get("point", "0")) if ENTRY_SECTION.match(name) else 0
        if not 1 <= point <= TRACK_MAX:
            continue
        data = _number(values.get("control", "0")) & DATA_CONTROL
        tracks.append(_track(point, None if data else TrackType.AUDIO, values.get("plba"), image))
    return tracks


def parse(text: str, image: str) -> Sheet:
    sections = _sections(text)
    sessions = next((values for name, values in sections if name == "disc"), {}).get("sessions")
    if sessions is not None and _number(sessions) > 1:
        raise FormatError(f"a CCD with {_number(sessions)} sessions; henkan reads one")
    tracks = _from_tracks(sections, image) or _from_entries(sections, image)
    if not tracks:
        raise FormatError("not a CCD: it names no track")
    return Sheet((image,), tuple(sorted(tracks, key=lambda track: track.number)))
