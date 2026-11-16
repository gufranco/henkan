from __future__ import annotations

import re

from henkan.formats import sfo
from henkan.formats.sectors import SECTOR
from henkan.formats.volume import Entry, Volume, find
from henkan.model import Platform
from henkan.platforms import ps3
from henkan.platforms.identity import UNKNOWN, Identity

CODE = r"\\?(?:[^\\/;\r\n]*[\\/])*([a-z]{4})[_-]?(\d{3})\.?(\d{2})"
BOOTS = (
    (Platform.PS2, "boot2", re.compile(r"boot2\s*=\s*cdrom0:" + CODE)),
    (Platform.PS1, "boot", re.compile(r"boot\s*=\s*cdrom:" + CODE)),
)
PSP_MARKERS = ("PSP_GAME", "UMD_DATA")
BOOT_FILE = "SYSTEM.CNF"


def _ps3(volume: Volume, folder: Entry) -> Identity:
    param = find(volume.children(folder), ps3.PARAM)
    if param is None:
        return Identity(Platform.PS3)
    return ps3.identity(volume.read(param, sfo.SIZE_MAX))


def _boot(volume: Volume, entry: Entry) -> Identity:
    text = volume.read(entry, SECTOR).decode("latin-1").casefold()
    for platform, marker, pattern in BOOTS:
        if marker not in text:
            continue
        match = pattern.search(text)
        code = f"{match[1].upper()}-{match[2]}{match[3]}" if match else ""
        return Identity(platform, code)
    return UNKNOWN


def identify(volume: Volume, *, ps3: bool) -> Identity:
    root = volume.root()
    folder = find(root, "PS3_GAME")
    if ps3 and folder is not None and folder.directory:
        return _ps3(volume, folder)
    if any(entry.name.upper().startswith(PSP_MARKERS) for entry in root):
        return Identity(Platform.PSP)
    boot = next((entry for entry in root if entry.name.upper().startswith(BOOT_FILE)), None)
    return UNKNOWN if boot is None else _boot(volume, boot)
