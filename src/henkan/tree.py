from __future__ import annotations

import os
from pathlib import Path

from henkan.errors import RefusalError

FILES_MAX = 2_000_000


def child(folder: Path | None, name: str) -> Path | None:
    if folder is None or not folder.is_dir():
        return None
    paths = sorted(folder.iterdir())
    wanted = name.casefold()
    exact = next((path for path in paths if path.name == name), None)
    return exact or next((path for path in paths if path.name.casefold() == wanted), None)


def measure(folder: Path, *, limit: int = FILES_MAX) -> tuple[int, int]:
    files = 0
    size = 0
    for parent, _, names in os.walk(folder):
        paths = [Path(parent) / name for name in names]
        regular = [path for path in paths if not path.is_symlink()]
        files += len(regular)
        if files > limit:
            raise RefusalError(f"{folder.name} holds more than {limit} files")
        size += sum(path.stat().st_size for path in regular)
    return files, size
