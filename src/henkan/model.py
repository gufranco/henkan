from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from henkan.formats.sheet import TrackType, known

CD_LIMIT = 737_280_000


class Platform(StrEnum):
    PS1 = "PS1"
    PS2 = "PS2"
    PSP = "PSP"
    PS3 = "PS3"
    DREAMCAST = "Dreamcast"
    SATURN = "Saturn"
    SEGA_CD = "Sega CD"
    GAMECUBE = "GameCube"
    WII = "Wii"
    WII_U = "Wii U"
    XBOX = "Xbox"
    XBOX_360 = "Xbox 360"
    SWITCH = "Switch"
    SWITCH_2 = "Switch 2"
    N3DS = "3DS"


class DiscClass(StrEnum):
    CD = "CD"
    DVD = "DVD"


class Format(StrEnum):
    CUE = "cue"
    GDI = "gdi"
    TOC = "toc"
    CCD = "ccd"
    MDS = "mds"
    ISO = "iso"
    BIN = "bin"
    PBP = "pbp"
    CHD = "chd"
    CDI = "cdi"
    VCD = "vcd"
    ECM = "ecm"
    CUE_ECC = "cue-ecc"
    ART = "art"
    CSO = "cso"
    CSO2 = "cso2"
    ZSO = "zso"
    RVZ = "rvz"
    WIA = "wia"
    GCZ = "gcz"
    CISO = "ciso"
    WBFS = "wbfs"
    WUD = "wud"
    WUX = "wux"
    XISO = "xiso"
    ZAR = "zar"
    FOLDER = "folder"
    PKG = "pkg"
    NUP = "nup"
    CCI = "cci"
    CXI = "cxi"
    HOMEBREW_3DS = "3dsx"
    ZCCI = "zcci"
    ZCXI = "zcxi"
    Z3DSX = "z3dsx"
    CIA = "cia"


class Trait(StrEnum):
    ENCRYPTED = "encrypted"
    FULL_DUMP = "full dump"
    HEURISTIC = "heuristic"
    NO_SHEET = "no sheet"
    PSN = "PSN"
    RAW = "raw"


@dataclass(frozen=True, slots=True)
class Item:
    path: Path
    kind: Format
    platform: Platform | None
    disc: DiscClass
    reason: str
    tracks: tuple[TrackType | None, ...]
    size: int
    files: tuple[Path, ...]
    game_id: str = ""
    title: str = ""
    region: str = ""
    discs: int = 1
    warnings: tuple[str, ...] = ()
    traits: frozenset[Trait] = frozenset()

    @property
    def types_known(self) -> bool:
        return bool(self.tracks) and all(known(kind) for kind in self.tracks)

    def has(self, trait: Trait) -> bool:
        return trait in self.traits


DVD_PLATFORMS = frozenset(
    {
        Platform.PSP,
        Platform.PS3,
        Platform.GAMECUBE,
        Platform.WII,
        Platform.WII_U,
        Platform.XBOX,
        Platform.XBOX_360,
        Platform.SWITCH,
        Platform.SWITCH_2,
        Platform.N3DS,
    }
)


def classify(platform: Platform | None, size: int) -> tuple[DiscClass, str]:
    if platform in DVD_PLATFORMS:
        return DiscClass.DVD, f"{platform} games use DVD-class discs"
    if size <= CD_LIMIT:
        return DiscClass.CD, f"{size:,} bytes fit a CD, which holds {CD_LIMIT:,}"
    return DiscClass.DVD, f"{size:,} bytes pass the CD limit of {CD_LIMIT:,}"
