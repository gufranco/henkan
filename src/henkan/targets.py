from __future__ import annotations

import re
from dataclasses import dataclass

from henkan.errors import UsageError
from henkan.formats.sheet import TrackType
from henkan.model import Format, Item, Platform, Trait

DISC_PICK = re.compile(r"([a-z0-9-]+?)(?:_d([1-9]\d?))?")
RAW_TYPES = (TrackType.MODE1_2352, TrackType.MODE2_2352)
UNPACKED_FIRST = (Format.PBP, Format.CCD, Format.MDS)
NINTENDO = (Format.RVZ, Format.ISO, Format.GCZ, Format.WIA, Format.CISO)
WII_KEYED = (Format.RVZ, Format.WIA, Format.WBFS)
COMPRESSED_3DS = {
    Format.CCI: Format.ZCCI,
    Format.CXI: Format.ZCXI,
    Format.HOMEBREW_3DS: Format.Z3DSX,
}
GD_ROM_TRACKS = 3
GD_ROM_KINDS = (Format.CUE, Format.GDI)


@dataclass(frozen=True, slots=True)
class Target:
    format: Format
    disc: int | None = None

    @property
    def name(self) -> str:
        return self.format.value if self.disc is None else f"{self.format.value}_d{self.disc}"


def parse(name: str) -> Target:
    match = DISC_PICK.fullmatch(name.lower())
    if match is None or match[1] not in Format:
        valid = ", ".join(sorted(Format))
        raise UsageError(f"{name!r} is not a target; the targets are: {valid}")
    return Target(Format(match[1]), int(match[2]) if match[2] else None)


def _single_track(item: Item) -> list[Format]:
    if len(item.tracks) != 1 or item.tracks[0] is TrackType.AUDIO:
        return []
    plain = item.kind is Format.ISO
    return [*([] if plain else [Format.ISO]), Format.CSO, Format.ZSO, Format.CSO2]


def _raw_tracks(item: Item) -> list[Format]:
    data = [kind for kind in item.tracks if kind is not TrackType.AUDIO]
    if any(kind not in RAW_TYPES for kind in data):
        return [Format.PBP] if item.platform is Platform.PS1 and item.kind is Format.ISO else []
    ps1 = item.platform is Platform.PS1
    mode2 = bool(data) and data[0] is TrackType.MODE2_2352
    wanted = [
        (Format.PBP, ps1 and item.kind is not Format.PBP),
        (Format.VCD, ps1 and mode2),
        (Format.CDI, True),
        (Format.CUE_ECC, True),
        (Format.ECM, len(item.tracks) == 1),
    ]
    return [target for target, offered in wanted if offered]


def _gd_rom(item: Item) -> bool:
    data = [kind is not TrackType.AUDIO for kind in item.tracks]
    shaped = len(data) >= GD_ROM_TRACKS and data[0] and data[GD_ROM_TRACKS - 1]
    return item.platform is Platform.DREAMCAST and item.kind in GD_ROM_KINDS and shaped


def _cd(item: Item) -> list[Target]:
    unpacked = item.types_known and item.kind in UNPACKED_FIRST
    found = [Format.CHD, *([Format.CUE] if unpacked else [])]
    if _gd_rom(item):
        found += [Format.GDI, Format.CUE]
    if item.kind is Format.PBP:
        found.append(Format.ART)
    if item.discs == 1 and item.types_known:
        found += [*_single_track(item), *_raw_tracks(item)]
    picks = [
        Target(kind, disc)
        for disc in range(1, item.discs + 1 if item.discs > 1 else 1)
        for kind in (Format.CHD, Format.CUE)
    ]
    return [*(Target(kind) for kind in found), *picks]


def _nintendo(item: Item, wii_key: bool) -> list[Format]:
    wii = item.platform is Platform.WII
    every = [*NINTENDO, *([Format.WBFS] if wii else [])]
    locked = WII_KEYED if wii and not wii_key else ()
    return [kind for kind in every if kind is not item.kind and kind not in locked]


def _xbox(item: Item) -> list[Format]:
    modern = item.platform is Platform.XBOX_360
    if item.kind is Format.FOLDER:
        return [Format.CHD, Format.ISO, *([Format.ZAR] if modern else [])]
    trimmed = [Format.XISO] if item.has(Trait.FULL_DUMP) and not modern else []
    return [Format.CHD, *([Format.ZAR] if modern else trimmed), Format.FOLDER]


def _ps3(item: Item) -> list[Format]:
    if item.has(Trait.PSN):
        return [Format.PKG]
    return [Format.ISO, Format.CHD] if item.kind is Format.FOLDER else [Format.CHD]


def _n3ds(item: Item) -> list[Format]:
    card = item.kind is Format.CCI and not item.has(Trait.ENCRYPTED)
    return [COMPRESSED_3DS[item.kind], *([Format.CIA] if card else [])]


def _console(item: Item, wii_key: bool) -> list[Format] | None:
    if item.platform in (Platform.GAMECUBE, Platform.WII):
        return _nintendo(item, wii_key)
    if item.platform in (Platform.XBOX, Platform.XBOX_360):
        return _xbox(item)
    simple = {
        Platform.WII_U: [Format.WUX],
        Platform.SWITCH: [Format.NUP],
        Platform.SWITCH_2: [Format.NUP],
    }
    if item.platform in simple:
        return simple[item.platform]
    by_console = {Platform.PS3: _ps3, Platform.N3DS: _n3ds}
    return by_console[item.platform](item) if item.platform in by_console else None


def offered(item: Item, *, wii_key: bool = False) -> tuple[Target, ...]:
    console = _console(item, wii_key)
    if console is None:
        return tuple(_cd(item))
    return tuple(Target(kind) for kind in console)
