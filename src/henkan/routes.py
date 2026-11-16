from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import StrEnum
from itertools import permutations

from henkan import targets
from henkan.errors import RefusalError
from henkan.model import Format, Item, Platform
from henkan.targets import Target


class Family(StrEnum):
    DISC = "disc"
    NINTENDO = "nintendo"
    WII_U = "wii u"
    XBOX = "xbox"
    PS3 = "ps3"
    SWITCH = "switch"
    N3DS = "3ds"


@dataclass(frozen=True, slots=True)
class Step:
    source: Format
    target: Format


@dataclass(frozen=True, slots=True)
class Plan:
    item: Item
    target: Target
    steps: tuple[Step, ...]
    temporary: int
    output: int


F = Format
DISC_STEPS = (
    *((source, F.CHD) for source in (F.CUE, F.GDI, F.TOC, F.ISO, F.BIN)),
    *((source, F.CUE) for source in (F.CCD, F.MDS, F.PBP, F.CDI, F.VCD, F.ECM, F.BIN, F.CHD)),
    *((F.CUE, target) for target in (F.CDI, F.VCD, F.PBP, F.ECM, F.CUE_ECC, F.ISO)),
    *((F.ISO, target) for target in (F.CSO, F.CSO2, F.ZSO)),
    *((source, F.ISO) for source in (F.CSO, F.CSO2, F.ZSO, F.BIN, F.CHD)),
    (F.CHD, F.GDI),
    *permutations((F.CUE, F.GDI), 2),
    (F.CUE, F.CUE),
    (F.GDI, F.GDI),
    (F.PBP, F.ART),
)
PAIRS = {
    Family.DISC: DISC_STEPS,
    Family.NINTENDO: tuple(permutations((F.ISO, F.RVZ, F.WIA, F.GCZ, F.CISO, F.WBFS), 2)),
    Family.WII_U: ((F.WUD, F.WUX), (F.WUX, F.WUD)),
    Family.XBOX: (
        *((F.ISO, target) for target in (F.CHD, F.XISO, F.FOLDER, F.ZAR)),
        *((F.FOLDER, target) for target in (F.ISO, F.ZAR)),
        *((F.ZAR, target) for target in (F.ISO, F.FOLDER)),
        (F.CHD, F.ISO),
    ),
    Family.PS3: (
        *((F.ISO, target) for target in (F.CHD, F.FOLDER)),
        *((F.FOLDER, target) for target in (F.ISO, F.PKG)),
        (F.PKG, F.FOLDER),
        (F.CHD, F.ISO),
    ),
    Family.SWITCH: ((F.FOLDER, F.NUP), (F.NUP, F.FOLDER)),
    Family.N3DS: (
        *permutations((F.CCI, F.ZCCI), 2),
        *permutations((F.CXI, F.ZCXI), 2),
        *permutations((F.HOMEBREW_3DS, F.Z3DSX), 2),
        *permutations((F.CCI, F.CIA), 2),
    ),
}
GRAPH = {
    family: frozenset(Step(source, target) for source, target in pairs)
    for family, pairs in PAIRS.items()
}
FAMILIES = {
    Platform.GAMECUBE: Family.NINTENDO,
    Platform.WII: Family.NINTENDO,
    Platform.WII_U: Family.WII_U,
    Platform.XBOX: Family.XBOX,
    Platform.XBOX_360: Family.XBOX,
    Platform.PS3: Family.PS3,
    Platform.SWITCH: Family.SWITCH,
    Platform.SWITCH_2: Family.SWITCH,
    Platform.N3DS: Family.N3DS,
}
PERCENT = {
    **dict.fromkeys((F.CSO, F.CSO2, F.ZSO, F.ZAR, F.ECM, F.WBFS), 95),
    **dict.fromkeys((F.PBP, F.RVZ, F.WIA, F.GCZ, F.ZCCI, F.ZCXI, F.Z3DSX), 80),
    F.CHD: 70,
    F.ART: 0,
}
WHOLE = 100
KEYED = (F.RVZ, F.WIA, F.WBFS)


def route(steps: frozenset[Step], source: Format, target: Format) -> tuple[Step, ...]:
    ordered = sorted(steps, key=lambda step: (step.source, step.target))
    reached: dict[Format, tuple[Step, ...]] = {}
    pending: deque[tuple[Format, tuple[Step, ...]]] = deque([(source, ())])
    while pending and target not in reached:
        current, path = pending.popleft()
        for step in ordered:
            if step.source is current and step.target not in reached:
                reached[step.target] = (*path, step)
                pending.append((step.target, reached[step.target]))
    if target not in reached:
        raise RefusalError(f"no chain of steps leads from {source} to {target}")
    return reached[target]


def _chosen(item: Item, name: str | None) -> Target:
    offered = targets.offered(item)
    if name is None:
        return offered[0]
    wanted = targets.parse(name)
    if wanted in offered:
        return wanted
    listed = ", ".join(target.name for target in offered)
    keyed = item.platform is Platform.WII and wanted.format in KEYED
    key = (
        f"; {wanted.name} needs the Wii common key, which this version of henkan does not read"
        if keyed
        else ""
    )
    raise RefusalError(
        f"{item.path.name} cannot become {wanted.name}; it can become: {listed}{key}"
    )


def plan(item: Item, name: str | None) -> Plan:
    target = _chosen(item, name)
    family = FAMILIES.get(item.platform, Family.DISC) if item.platform else Family.DISC
    steps = route(GRAPH[family], item.kind, target.format)
    size = item.size if target.disc is None else item.size // item.discs
    output = size * PERCENT.get(target.format, WHOLE) // WHOLE
    return Plan(item, target, steps, size * (len(steps) - 1), output)
