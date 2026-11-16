from __future__ import annotations

from henkan.model import Platform

SIGNATURES = (
    (b"SEGA SEGAKATANA", Platform.DREAMCAST),
    (b"SEGA SEGASATURN", Platform.SATURN),
    (b"SEGADISCSYSTEM", Platform.SEGA_CD),
    (b"SEGA MEGA DRIVE", Platform.SEGA_CD),
)


def identify(boot: bytes) -> Platform | None:
    return next((platform for start, platform in SIGNATURES if boot.startswith(start)), None)
