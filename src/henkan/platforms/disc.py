from __future__ import annotations

from henkan.errors import FormatError
from henkan.formats import iso9660, udf
from henkan.formats.sectors import COOKED, LAYOUTS, SECTOR, SectorView
from henkan.formats.volume import Volume
from henkan.model import Platform
from henkan.platforms import sega, sony
from henkan.platforms.identity import UNKNOWN, Identity
from henkan.source import Source

PS3_SECTORS_MIN = 19


def _volume(view: SectorView) -> Volume:
    try:
        return iso9660.read_volume(view)
    except FormatError:
        return udf.read_volume(view)


def _sony(view: SectorView) -> Identity:
    cooked = view.layout is COOKED and view.source.size - view.base >= PS3_SECTORS_MIN * SECTOR
    try:
        volume = _volume(view)
        ps3 = cooked and isinstance(volume, iso9660.IsoVolume)
        return sony.identify(volume, ps3=ps3)
    except FormatError:
        return UNKNOWN


def _probe(view: SectorView) -> Identity:
    try:
        boot = view.sector(0)
    except FormatError:
        return UNKNOWN
    console = sega.identify(boot)
    if console is Platform.DREAMCAST:
        return Identity(console)
    found = _sony(view)
    return found if found.platform else Identity(console)


def sniff(source: Source, base: int = 0) -> Identity:
    probes = (_probe(SectorView(source, layout, base)) for layout in LAYOUTS)
    return next((found for found in probes if found.platform), UNKNOWN)


def holds_volume(source: Source) -> bool:
    try:
        _volume(SectorView(source, COOKED))
    except FormatError:
        return False
    return True
