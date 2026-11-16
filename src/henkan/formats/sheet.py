from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from henkan.errors import FormatError
from henkan.source import Source

SHEET_MAX = 1024 * 1024
FRAMES_PER_SECOND = 75
TRACK_MAX = 99


class TrackType(StrEnum):
    AUDIO = "AUDIO"
    MODE1_2048 = "MODE1/2048"
    MODE1_2352 = "MODE1/2352"
    MODE2_2352 = "MODE2/2352"
    MODE2_2336 = "MODE2/2336"


STRIDES = {
    TrackType.AUDIO: 2352,
    TrackType.MODE1_2048: 2048,
    TrackType.MODE1_2352: 2352,
    TrackType.MODE2_2352: 2352,
    TrackType.MODE2_2336: 2336,
}


@dataclass(frozen=True, slots=True)
class Track:
    number: int
    kind: TrackType | None
    file: str
    start: int
    stride: int
    offset: int


@dataclass(frozen=True, slots=True)
class Sheet:
    files: tuple[str, ...]
    tracks: tuple[Track, ...]


def known(kind: TrackType | None) -> bool:
    return kind is not None and kind is not TrackType.MODE2_2336


def text(source: Source) -> str:
    if source.size > SHEET_MAX:
        raise FormatError(
            f"{source.name}: a sheet of {source.size} bytes passes the limit of {SHEET_MAX}"
        )
    data = source.read(0, source.size)
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("latin-1")
