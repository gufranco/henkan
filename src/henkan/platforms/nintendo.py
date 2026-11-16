from __future__ import annotations

from henkan.model import Platform
from henkan.platforms.identity import UNKNOWN, Identity
from henkan.source import Source

HEADER_SIZE = 0x60
WII_MAGIC = bytes.fromhex("5D1C9EA3")
GAMECUBE_MAGIC = bytes.fromhex("C2339F3D")
WII_U_PREFIX = b"WUP-"
WII_U_CODE = slice(6, 10)
REGIONS = {"E": "USA", "P": "Europe", "J": "Japan", "K": "Korea"}
REGION_LETTER = 3


def _text(raw: bytes) -> str:
    return raw.partition(b"\0")[0].decode("ascii", errors="replace").strip()


def identify(source: Source) -> Identity:
    head = source.peek(0, HEADER_SIZE)
    if head.startswith(WII_U_PREFIX) and len(head) >= WII_U_CODE.stop:
        return Identity(Platform.WII_U, _text(head[WII_U_CODE]))
    wii = head[0x18:0x1C] == WII_MAGIC
    if len(head) < HEADER_SIZE or not (wii or head[0x1C:0x20] == GAMECUBE_MAGIC):
        return UNKNOWN
    code = _text(head[:6])
    region = REGIONS.get(code[REGION_LETTER : REGION_LETTER + 1], "")
    return Identity(Platform.WII if wii else Platform.GAMECUBE, code, _text(head[0x20:]), region)
