from __future__ import annotations

from dataclasses import dataclass

from henkan.model import Platform


@dataclass(frozen=True, slots=True)
class Identity:
    platform: Platform | None = None
    game_id: str = ""
    title: str = ""
    region: str = ""


UNKNOWN = Identity()
