from __future__ import annotations

import os
from collections.abc import Mapping

from henkan.errors import HenkanError

READ_MAX_VARIABLE = "HENKAN_READ_MAX"
DEFAULT_READ_MAX = 64 * 1024 * 1024


def read_max(environ: Mapping[str, str] | None = None) -> int:
    raw = (os.environ if environ is None else environ).get(READ_MAX_VARIABLE)
    if raw is None:
        return DEFAULT_READ_MAX
    if not (raw.isascii() and raw.isdigit()) or int(raw) == 0:
        raise HenkanError(
            f"{READ_MAX_VARIABLE} must be a whole number of bytes above zero, not {raw!r}"
        )
    return int(raw)
