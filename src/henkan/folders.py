from __future__ import annotations

from pathlib import Path

from henkan import tree
from henkan.errors import UnsupportedError
from henkan.model import Format, Item, Trait, classify
from henkan.platforms import ps3, switch, xbox
from henkan.platforms.identity import Identity

IMAGE_OVERHEAD = 4 * 0x10000
UNCERTAIN = "main.npdm does not tell Switch from Switch 2, so this is taken as Switch"


def _item(
    path: Path,
    identity: Identity,
    size: int,
    *,
    reason: str = "",
    warnings: tuple[str, ...] = (),
    traits: frozenset[Trait] = frozenset(),
) -> Item:
    disc_class, console = classify(identity.platform, size)
    return Item(
        path=path,
        kind=Format.FOLDER,
        platform=identity.platform,
        disc=disc_class,
        reason=reason or console,
        tracks=(),
        size=size,
        files=(path,),
        game_id=identity.game_id,
        title=identity.title,
        region=identity.region,
        warnings=warnings,
        traits=traits,
    )


def _switch(path: Path, found: switch.SwitchFolder) -> Item:
    files, size = tree.measure(path)
    reason = (
        f"a decrypted {found.platform} game folder: 1 game, {found.updates} updates, "
        f"{found.extras} extra content, {files} files"
    )
    return _item(
        path,
        Identity(found.platform, found.title_id),
        size,
        reason=reason,
        warnings=() if found.certain else (UNCERTAIN,),
        traits=frozenset({Trait.HEURISTIC}),
    )


def _console(path: Path) -> tuple[Identity, frozenset[Trait]] | None:
    psn = ps3.psn_folder(path)
    if psn is not None:
        return psn, frozenset({Trait.PSN})
    disc = ps3.disc_folder(path)
    platform = xbox.folder(path)
    found = disc or (Identity(platform) if platform else None)
    return None if found is None else (found, frozenset())


def analyze(path: Path) -> Item:
    game = switch.detect(path)
    if game is not None:
        return _switch(path, game)
    found = _console(path)
    if found is None:
        raise UnsupportedError(
            f"{path.name} is not a recognized Switch, PS3, Xbox or Xbox 360 game folder: it has "
            "no exefs beside romfs, no PS3_GAME, no PARAM.SFO beside USRDIR, no default.xex and "
            "no default.xbe at its top"
        )
    _, size = tree.measure(path)
    return _item(path, found[0], size + IMAGE_OVERHEAD, traits=found[1])
