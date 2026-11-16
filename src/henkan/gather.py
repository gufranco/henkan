from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

from henkan import detect, tree
from henkan.errors import HenkanError, OrphanError, RefusalError, UnsupportedError
from henkan.model import Item

SKIPPED_FOLDERS = ("$recycle.bin", "system volume information")
TEMPORARY_PREFIX = ".henkan-"
ORPHANS = "left out: an MDF holds track data only and cannot be read without its MDS descriptor"


@dataclass(frozen=True, slots=True)
class Refused:
    path: Path
    reason: str
    orphan: bool = False


@dataclass(frozen=True, slots=True)
class Gathered:
    items: tuple[Item, ...]
    refused: tuple[Refused, ...]
    notes: tuple[str, ...]


type Outcome = Item | Refused


def _outcome(path: Path, *, named: bool) -> Outcome | None:
    try:
        return detect.inspect(path)
    except OrphanError as error:
        return Refused(path, str(error), orphan=True)
    except UnsupportedError as error:
        return Refused(path, str(error)) if named else None
    except HenkanError as error:
        return Refused(path, str(error))


def _skipped(entry: Path) -> bool:
    name = entry.name.casefold()
    system = name in SKIPPED_FOLDERS or name.startswith(TEMPORARY_PREFIX)
    return entry.is_symlink() or (system and entry.is_dir())


def _walk(folder: Path, limit: int) -> Iterator[Outcome]:
    pending = [folder]
    seen = 0
    while pending:
        entries = sorted(pending.pop().iterdir())
        seen += len(entries)
        if seen > limit:
            raise RefusalError(f"{folder.name} holds more than {limit} entries")
        for entry in (entry for entry in entries if not _skipped(entry)):
            outcome = _outcome(entry, named=False)
            if outcome is not None:
                yield outcome
            elif entry.is_dir():
                pending.append(entry)


def _named(path: Path, limit: int) -> list[Outcome]:
    outcome = _outcome(path, named=not path.is_dir())
    if outcome is not None:
        return [outcome]
    try:
        found = sorted(_walk(path, limit), key=lambda outcome: outcome.path)
    except RefusalError as error:
        return [Refused(path, str(error))]
    return found or [Refused(path, f"{path.name} holds nothing henkan can convert")]


def _notes(owners: dict[Path, Path], orphans: int, named: Sequence[Path]) -> tuple[str, ...]:
    covered = dict.fromkeys(path for path in named if path.resolve() in owners)
    parts = [f"{path.name} is part of {owners[path.resolve()].name}" for path in covered]
    if orphans:
        parts.append(f"{orphans} MDF files {ORPHANS}")
    return tuple(parts)


def gather(paths: Sequence[Path], *, limit: int = tree.FILES_MAX) -> Gathered:
    outcomes = [outcome for path in dict.fromkeys(paths) for outcome in _named(path, limit)]
    found = [outcome for outcome in outcomes if isinstance(outcome, Item)]
    unique = {item.path.resolve(): item for item in reversed(found)}
    owners = {
        file.resolve(): item.path
        for item in unique.values()
        for file in item.files
        if file != item.path
    }
    items = tuple(item for item in reversed(unique.values()) if item.path.resolve() not in owners)
    refused = [outcome for outcome in outcomes if isinstance(outcome, Refused)]
    stray = [entry for entry in refused if entry.orphan and entry.path not in paths]
    kept = tuple(
        entry for entry in refused if entry not in stray and entry.path.resolve() not in owners
    )
    return Gathered(items, kept, _notes(owners, len(stray), paths))
