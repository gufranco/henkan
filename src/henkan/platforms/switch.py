from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from henkan import tree
from henkan.errors import RefusalError
from henkan.model import Platform

META = b"META"
ACI0 = b"ACI0"
ACID = b"ACID"
ACI0_POINTER = slice(0x70, 0x74)
ACID_POINTER = slice(0x78, 0x7C)
TITLE_AT = 0x10
GENERATIONS = ((0x200, Platform.SWITCH), (0x300, Platform.SWITCH_2))
NPDM_MAX = 1024 * 1024
TITLE_TOKEN = re.compile(r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{16}(?![0-9A-Fa-f])")
DIGITS = re.compile(r"\d{1,10}")
HEX16 = re.compile(r"[0-9A-Fa-f]{16}")


@dataclass(frozen=True, slots=True)
class SwitchFolder:
    platform: Platform
    certain: bool
    title_id: str
    updates: int
    extras: int


def _holds_files(folder: Path | None) -> bool:
    return folder is not None and any(path.is_file() for path in folder.rglob("*"))


def _package(folder: Path) -> bool:
    return any(_holds_files(tree.child(folder, name)) for name in ("exefs", "romfs"))


def _plain(folder: Path) -> bool:
    code, data = tree.child(folder, "exefs"), tree.child(folder, "romfs")
    if code is None or data is None:
        return False
    return any(tree.child(code, name) is not None for name in ("main", "main.npdm"))


def _named(parent: Path | None, pattern: re.Pattern[str]) -> list[Path]:
    if parent is None or not parent.is_dir():
        return []
    return [path for path in sorted(parent.iterdir()) if pattern.fullmatch(path.name)]


def _layout(folder: Path) -> tuple[Path, int, int] | None:
    base = tree.child(folder, "base")
    if base is None or not _package(base):
        return (folder, 0, 0) if _plain(folder) else None
    updates = [path for path in _named(tree.child(folder, "updates"), DIGITS) if _package(path)]
    titles = _named(tree.child(folder, "dlc"), HEX16)
    extras = [path for title in titles for path in _named(title, DIGITS) if _package(path)]
    return base, len(updates), len(extras)


def _npdm(base: Path) -> bytes:
    path = tree.child(tree.child(base, "exefs"), "main.npdm")
    if path is None or not path.is_file():
        return b""
    with path.open("rb") as handle:
        data = handle.read(NPDM_MAX)
    return data if data.startswith(META) else b""


def _title_id(npdm: bytes, folder: Path) -> str:
    at = int.from_bytes(npdm[ACI0_POINTER], "little")
    if npdm[at : at + len(ACI0)] != ACI0:
        at = npdm.find(ACI0)
    value = npdm[at + TITLE_AT : at + TITLE_AT + 8] if at >= 0 else b""
    token = TITLE_TOKEN.search(folder.name)
    if len(value) == 8:
        return f"{int.from_bytes(value, 'little'):016X}"
    if token is None:
        raise RefusalError(
            f"{folder.name}: no title ID in main.npdm or in the folder name; name the folder "
            "with the 16-digit title ID, for example `Game [0100000000010000]`"
        )
    return token[0].upper()


def _generation(npdm: bytes) -> Platform | None:
    at = int.from_bytes(npdm[ACID_POINTER], "little")
    marks = ((npdm[at + gap : at + gap + len(ACID)], platform) for gap, platform in GENERATIONS)
    return next((platform for mark, platform in marks if mark == ACID), None)


def detect(folder: Path) -> SwitchFolder | None:
    layout = _layout(folder)
    if layout is None:
        return None
    base, updates, extras = layout
    npdm = _npdm(base)
    generation = _generation(npdm)
    title = _title_id(npdm, folder)
    return SwitchFolder(
        generation or Platform.SWITCH, generation is not None, title, updates, extras
    )
