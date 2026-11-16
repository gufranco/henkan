from __future__ import annotations

import re
from pathlib import Path

from henkan import tree
from henkan.errors import FormatError
from henkan.formats import sfo
from henkan.model import Platform
from henkan.platforms.identity import Identity

REGIONS = {"U": "USA", "E": "Europe", "J": "Japan", "A": "Asia", "K": "Korea", "H": "Hong Kong"}
REGION_LETTER = 2
DISC_CATEGORY = "DG"
TITLE_ID = re.compile(r"[A-Z]{4}\d{5}")
GAME_FOLDER = "PS3_GAME"
PARAM = "PARAM.SFO"


def _identity(values: dict[str, str | int]) -> Identity:
    code = sfo.text(values, "TITLE_ID").replace("-", "")
    region = REGIONS.get(code[REGION_LETTER : REGION_LETTER + 1], "")
    return Identity(Platform.PS3, code, sfo.text(values, "TITLE"), region)


def identity(data: bytes) -> Identity:
    try:
        return _identity(sfo.parse(data))
    except FormatError:
        return Identity(Platform.PS3)


def _read(path: Path) -> bytes:
    with path.open("rb") as handle:
        return handle.read(sfo.SIZE_MAX)


def disc_folder(folder: Path) -> Identity | None:
    param = tree.child(tree.child(folder, GAME_FOLDER), PARAM)
    if param is None or not param.is_file():
        return None
    return identity(_read(param))


def psn_folder(folder: Path) -> Identity | None:
    param, data = tree.child(folder, PARAM), tree.child(folder, "USRDIR")
    if param is None or data is None or tree.child(folder, GAME_FOLDER) is not None:
        return None
    try:
        values = sfo.parse(_read(param))
    except FormatError:
        return None
    found = _identity(values)
    disc = sfo.text(values, "CATEGORY") == DISC_CATEGORY
    return None if disc or TITLE_ID.fullmatch(found.game_id) is None else found
