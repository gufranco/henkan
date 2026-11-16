from __future__ import annotations

import re
from pathlib import Path

from henkan import folders, images, sheets, tree, unread
from henkan.errors import OrphanError, RefusalError, UnsupportedError
from henkan.formats import pbp
from henkan.formats.sheet import TrackType
from henkan.model import DiscClass, Format, Item, Platform, Trait, classify
from henkan.platforms import n3ds, xbox
from henkan.source import Source, open_source

STAND_INS = {".mdf": ".mds", ".sub": ".ccd"}
ORPHAN = ".mdf"
SONY_CODE = re.compile(r"([A-Z]{4})(\d{5})")
PBP_TRACKS = (TrackType.MODE2_2352, TrackType.AUDIO)
ENCRYPTED = "an encrypted dump can be compressed, but emulators run only decrypted dumps"


def _n3ds(path: Path, source: Source) -> Item | None:
    found = n3ds.identify(source)
    if found is None:
        return None
    kind, decrypted = found
    disc, reason = classify(Platform.N3DS, source.size)
    return Item(
        path=path,
        kind=kind,
        platform=Platform.N3DS,
        disc=disc,
        reason=reason,
        tracks=(),
        size=source.size,
        files=(path,),
        warnings=() if decrypted else (ENCRYPTED,),
        traits=frozenset() if decrypted else frozenset({Trait.ENCRYPTED}),
    )


def _pbp(path: Path, source: Source) -> Item | None:
    if source.peek(0, len(pbp.MAGIC)) != pbp.MAGIC:
        return None
    found = pbp.read(source)
    code = SONY_CODE.fullmatch(found.disc_id)
    return Item(
        path=path,
        kind=Format.PBP,
        platform=Platform.PS1,
        disc=DiscClass.CD,
        reason="a PBP holds PS1 CDs",
        tracks=PBP_TRACKS,
        size=source.size * 8 // 5,
        files=(path,),
        game_id=f"{code[1]}-{code[2]}" if code else found.disc_id,
        discs=found.discs,
    )


def _unread(path: Path, source: Source) -> Item | None:
    label = unread.label(source, path.suffix.casefold())
    if label is None:
        return None
    raise RefusalError(f"{path.name} is {label}, which this version of henkan does not read")


ANALYZERS = (_n3ds, _pbp, _unread, sheets.analyze, images.analyze)


def analyze(path: Path, source: Source) -> Item:
    if source.size == 0:
        raise RefusalError(f"{path.name} is empty")
    if path.suffix.casefold() == ORPHAN:
        raise OrphanError(
            f"{path.name} holds track data only and cannot be read without its MDS descriptor"
        )
    package = xbox.package_kind(source)
    if package is not None:
        raise RefusalError(
            f"{path.name} is an Xbox 360 {package} package, not a disc; it needs no conversion, "
            "since emulators load such packages directly"
        )
    found = (analyze(path, source) for analyze in ANALYZERS)
    item = next((item for item in found if item is not None), None)
    if item is None:
        raise UnsupportedError(f"{path.name} is not a kind of file henkan converts")
    return item


def stand_in(path: Path) -> Path:
    extension = STAND_INS.get(path.suffix.casefold())
    described = tree.child(path.parent, path.stem + extension) if extension else None
    return path if described is None else described


def inspect(path: Path) -> Item:
    if path.is_dir():
        return folders.analyze(path)
    if not path.is_file():
        raise RefusalError(f"{path.name}: no such file or folder")
    target = stand_in(path)
    with open_source(target) as source:
        return analyze(target, source)
