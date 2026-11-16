from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from henkan import routes, targets
from henkan.errors import RefusalError
from henkan.gather import Refused, gather
from henkan.model import Item
from henkan.routes import Plan
from henkan.targets import Target


@dataclass(frozen=True, slots=True)
class Offer:
    item: Item
    targets: tuple[Target, ...]


@dataclass(frozen=True, slots=True)
class Report[Entry]:
    entries: tuple[Entry, ...]
    refused: tuple[Refused, ...]
    notes: tuple[str, ...]


def info(paths: Sequence[Path]) -> Report[Item]:
    found = gather(paths)
    return Report(found.items, found.refused, found.notes)


def offers(paths: Sequence[Path]) -> Report[Offer]:
    found = gather(paths)
    entries = tuple(Offer(item, targets.offered(item)) for item in found.items)
    return Report(entries, found.refused, found.notes)


def _plan(item: Item, target: str | None) -> Plan | Refused:
    try:
        return routes.plan(item, target)
    except RefusalError as error:
        return Refused(item.path, str(error))


def plans(paths: Sequence[Path], target: str | None) -> Report[Plan]:
    if target is not None:
        targets.parse(target)
    found = gather(paths)
    outcomes = [_plan(item, target) for item in found.items]
    planned = tuple(outcome for outcome in outcomes if isinstance(outcome, Plan))
    refused = tuple(outcome for outcome in outcomes if isinstance(outcome, Refused))
    return Report(planned, (*found.refused, *refused), found.notes)
