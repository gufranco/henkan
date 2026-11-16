from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from henkan.errors import RefusalError
from henkan.formats.sectors import RAW_SECTOR, SECTOR, raw_mode
from henkan.formats.sheet import TrackType
from henkan.model import DiscClass, Format, Item, Platform, Trait, classify
from henkan.platforms import disc, nintendo, xbox
from henkan.platforms.identity import Identity
from henkan.source import Source

PLAIN_EXTENSIONS = (".iso", ".img")
LONE_EXTENSIONS = (".bin", ".img")
NINTENDO_EXTENSIONS = (".gcm", ".wud")
IMAGE_EXTENSIONS = (".iso", *LONE_EXTENSIONS, *NINTENDO_EXTENSIONS)
RAW_KINDS = {1: TrackType.MODE1_2352, 2: TrackType.MODE2_2352}
RAW_REASON = "raw CD sectors make a CD whatever the size"
LONE_WARNING = "no sheet describes this BIN, so its one track is taken as Mode 2 raw"
COOKED = (TrackType.MODE1_2048,)


def _item(
    path: Path,
    source: Source,
    kind: Format,
    identity: Identity,
    tracks: tuple[TrackType, ...] = (),
    traits: frozenset[Trait] = frozenset(),
) -> Item:
    disc_class, reason = classify(identity.platform, source.size)
    return Item(
        path=path,
        kind=kind,
        platform=identity.platform,
        disc=disc_class,
        reason=reason,
        tracks=tracks,
        size=source.size,
        files=(path,),
        game_id=identity.game_id,
        title=identity.title,
        region=identity.region,
        traits=traits,
    )


def _raw(path: Path, source: Source, mode: int) -> Item:
    item = _item(path, source, Format.BIN, disc.sniff(source), (RAW_KINDS[mode],))
    return replace(item, disc=DiscClass.CD, reason=RAW_REASON, traits=frozenset({Trait.RAW}))


def _console(path: Path, source: Source) -> Item | None:
    identity = nintendo.identify(source)
    if identity.platform:
        kind = Format.WUD if identity.platform is Platform.WII_U else Format.ISO
        return _item(path, source, kind, identity)
    found = xbox.identify(source)
    if found is None:
        return None
    traits = frozenset({Trait.FULL_DUMP}) if found[1] else frozenset()
    return _item(path, source, Format.ISO, Identity(found[0]), traits=traits)


def _lone(path: Path, source: Source, extension: str) -> Item:
    cooked = source.size % SECTOR == 0
    if extension == ".img" and cooked:
        return _item(path, source, Format.ISO, Identity(), COOKED)
    if extension == ".img" or (not cooked and source.size % RAW_SECTOR):
        raise RefusalError(
            f"{path.name} is cut short or not made of whole sectors: {source.size} bytes is no "
            f"multiple of {SECTOR} or {RAW_SECTOR}"
        )
    item = _item(path, source, Format.BIN, Identity(), (TrackType.MODE2_2352,))
    return replace(
        item,
        disc=DiscClass.CD,
        reason=RAW_REASON,
        warnings=(LONE_WARNING,),
        traits=frozenset({Trait.NO_SHEET}),
    )


def _sized(path: Path, source: Source, extension: str) -> Item | None:
    mode = raw_mode(source)
    if mode is not None:
        return _raw(path, source, mode)
    found = _console(path, source)
    if found is not None:
        return found
    identity = disc.sniff(source)
    if identity.platform or extension == ".iso" or disc.holds_volume(source):
        return _item(path, source, Format.ISO, identity, COOKED)
    if extension in NINTENDO_EXTENSIONS:
        raise RefusalError(f"{path.name} is corrupt or not a disc image")
    return _lone(path, source, extension) if extension in LONE_EXTENSIONS else None


def analyze(path: Path, source: Source) -> Item | None:
    extension = path.suffix.casefold()
    if source.size > SECTOR:
        return _sized(path, source, extension)
    if extension not in IMAGE_EXTENSIONS:
        return None
    raise RefusalError(
        f"{path.name} is too small to be a disc image: {source.size} bytes, when an image holds "
        f"more than one sector of {SECTOR} or {RAW_SECTOR} bytes"
    )
