from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

from henkan import tree
from henkan.errors import FormatError, RefusalError
from henkan.formats import ccd, cue, gdi, mds, sheet, toc
from henkan.formats.sectors import RAW_SECTOR, SECTOR, raw_mode
from henkan.formats.sheet import SHEET_MAX, Sheet, Track, TrackType
from henkan.model import DiscClass, Format, Item, Platform
from henkan.platforms import disc
from henkan.platforms.identity import UNKNOWN, Identity
from henkan.source import Source, open_source

PROBE = 4096
EXTENSIONS = {".cue": Format.CUE, ".gdi": Format.GDI, ".toc": Format.TOC, ".ccd": Format.CCD}
MARKERS = (
    (Format.CCD, re.compile(r"\[(?:clonecd|disc)\]$", re.IGNORECASE)),
    (Format.CUE, re.compile(r"TRACK\s+\d+\s+\S+", re.IGNORECASE)),
    (Format.TOC, re.compile(r"(?:CD_DA|CD_ROM|CD_ROM_XA)$|TRACK\s+[A-Z]", re.IGNORECASE)),
)
SNIFFED_STRIDES = (SECTOR, RAW_SECTOR)
BY_STRIDE = {2048: TrackType.MODE1_2048, 2336: TrackType.MODE2_2336}
BY_MODE = {1: TrackType.MODE1_2352, 2: TrackType.MODE2_2352}
TYPED_BY_SHEET = (Format.CUE, Format.GDI)
SUBCHANNEL = ".sub"
IMAGE = ".img"


def _kind(text: str, extension: str) -> Format | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) > 1 and gdi.COUNT.match(lines[0]) and gdi.LINE.match(lines[1]):
        return Format.GDI
    marked = (kind for kind, marker in MARKERS if any(marker.match(line) for line in lines))
    return next(marked, EXTENSIONS.get(extension))


def _parse(kind: Format, text: str, path: Path) -> Sheet:
    if kind is Format.CCD:
        return ccd.parse(text, path.stem + IMAGE)
    return {Format.CUE: cue.parse, Format.GDI: gdi.parse, Format.TOC: toc.parse}[kind](text)


def _locate(folder: Path, name: str) -> Path | None:
    last = name.replace("\\", "/").rpartition("/")[2]
    found = tree.child(folder, last) if last else None
    return found if found is not None and found.is_file() else None


def _mds(path: Path, source: Source) -> Sheet:
    parsed = mds.parse(source)
    names = mds.candidates(parsed.files[0], path.stem)
    name = next((name for name in names if _locate(path.parent, name)), names[0])
    return Sheet((name,), tuple(replace(track, file=name) for track in parsed.tracks))


def _typed(track: Track, path: Path) -> TrackType:
    if track.stride in BY_STRIDE:
        return BY_STRIDE[track.stride]
    with open_source(path) as data:
        return BY_MODE.get(raw_mode(data, track.offset) or 0, TrackType.AUDIO)


def _tracks(kind: Format, parsed: Sheet, files: dict[str, Path]) -> tuple[Track, ...]:
    if kind in TYPED_BY_SHEET:
        return parsed.tracks
    return tuple(
        track if track.kind else replace(track, kind=_typed(track, files[track.file]))
        for track in parsed.tracks
    )


def _identity(tracks: tuple[Track, ...], files: dict[str, Path]) -> Identity:
    data = next((track for track in tracks if track.kind is not TrackType.AUDIO), None)
    first = next(iter(files.values()))
    places = [(files[data.file], data.offset)] if data and data.stride in SNIFFED_STRIDES else []
    for path, base in (*places, (first, 0)):
        with open_source(path) as source:
            found = disc.sniff(source, base)
        if found.platform:
            return found
    return UNKNOWN


def _extras(kind: Format, path: Path, files: dict[str, Path]) -> tuple[Path, ...]:
    if kind is not Format.CCD:
        return ()
    image = files[path.stem + IMAGE]
    if image.stat().st_size % RAW_SECTOR:
        raise FormatError(f"{image.name} is not made of whole {RAW_SECTOR}-byte sectors")
    side = tree.child(path.parent, path.stem + SUBCHANNEL)
    return () if side is None else (side,)


def _item(path: Path, kind: Format, parsed: Sheet) -> Item:
    found = {name: _locate(path.parent, name) for name in parsed.files}
    files = {name: where for name, where in found.items() if where is not None}
    if len(files) < len(found):
        missing = ", ".join(name for name in found if name not in files)
        raise RefusalError(f"{path.name} names files that are missing: {missing}")
    extras = _extras(kind, path, files)
    tracks = _tracks(kind, parsed, files)
    dreamcast = Identity(Platform.DREAMCAST)
    identity = dreamcast if kind is Format.GDI else _identity(tracks, files)
    return Item(
        path=path,
        kind=kind,
        platform=identity.platform,
        disc=DiscClass.CD,
        reason=f"a {kind.upper()} sheet describes a CD",
        tracks=tuple(track.kind for track in tracks),
        size=sum(where.stat().st_size for where in files.values()),
        files=(path, *files.values(), *extras),
        game_id=identity.game_id,
    )


def analyze(path: Path, source: Source) -> Item | None:
    if source.peek(0, len(mds.MAGIC)) == mds.MAGIC:
        return _item(path, Format.MDS, _mds(path, source))
    if source.size > SHEET_MAX or b"\0" in source.peek(0, PROBE):
        return None
    text = sheet.text(source)
    extension = path.suffix.casefold()
    kind = _kind(text, extension)
    if kind is None:
        return None
    try:
        parsed = _parse(kind, text, path)
    except FormatError:
        if extension in EXTENSIONS:
            raise
        return None
    return _item(path, kind, parsed)
