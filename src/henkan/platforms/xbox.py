from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from henkan import tree
from henkan.errors import FormatError
from henkan.formats import xdvdfs
from henkan.model import Platform
from henkan.source import Source

BOOT_FILES = (("default.xex", Platform.XBOX_360), ("default.xbe", Platform.XBOX))
PACKAGE_MAGICS = (b"LIVE", b"PIRS", b"CON ")
CONTENT_TYPE_AT = 0x344
PLAIN_PACKAGE = "download"
PACKAGE_KINDS = {
    0x7000: "Games on Demand",
    0xD0000: "Xbox Live Arcade",
    0xB0000: "title update",
    0x2: "downloadable content",
    0x4000: "installed game",
    0x1000: "downloaded Xbox 360 title",
    0x1: "saved game",
    0x80000: "game demo",
}


def _platform(names: Iterable[str]) -> Platform | None:
    present = {name.casefold() for name in names}
    return next((platform for name, platform in BOOT_FILES if name in present), None)


def identify(source: Source) -> tuple[Platform, int] | None:
    try:
        volume = xdvdfs.read_volume(source)
        platform = _platform(volume.names())
    except FormatError:
        return None
    return None if platform is None else (platform, volume.base)


def package_kind(source: Source) -> str | None:
    if source.peek(0, 4) not in PACKAGE_MAGICS:
        return None
    content = int.from_bytes(source.peek(CONTENT_TYPE_AT, 4), "big")
    return PACKAGE_KINDS.get(content, PLAIN_PACKAGE)


def folder(path: Path) -> Platform | None:
    files = (
        name for name, _ in BOOT_FILES if (found := tree.child(path, name)) and found.is_file()
    )
    return _platform(files)
