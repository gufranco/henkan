from __future__ import annotations

from henkan.commands import Offer
from henkan.model import Item
from henkan.routes import Plan

LABEL_WIDTH = 10
UNKNOWN = "unknown"

type Json = dict[str, object]


def _row(label: str, value: str) -> str:
    return f"  {label:<{LABEL_WIDTH}}{value}"


def _platform(item: Item) -> str:
    return item.platform or UNKNOWN


def info_lines(item: Item) -> list[str]:
    rows = (
        ("kind", item.kind.value),
        ("platform", _platform(item)),
        ("disc", f"{item.disc}: {item.reason}"),
        ("id", item.game_id),
        ("title", item.title),
        ("region", item.region),
        ("discs", str(item.discs) if item.discs > 1 else ""),
        ("tracks", ", ".join(kind or UNKNOWN for kind in item.tracks)),
        ("size", f"{item.size:,} bytes"),
        ("files", ", ".join(path.name for path in item.files)),
        ("traits", ", ".join(sorted(item.traits))),
        *(("warning", warning) for warning in item.warnings),
    )
    return [str(item.path), *(_row(label, value) for label, value in rows if value)]


def item_json(item: Item) -> Json:
    return {
        "path": str(item.path),
        "kind": item.kind.value,
        "platform": item.platform,
        "disc": item.disc.value,
        "reason": item.reason,
        "id": item.game_id,
        "title": item.title,
        "region": item.region,
        "discs": item.discs,
        "tracks": list(item.tracks),
        "size": item.size,
        "files": [str(path) for path in item.files],
        "traits": sorted(item.traits),
        "warnings": list(item.warnings),
    }


def offer_lines(offer: Offer) -> list[str]:
    item = offer.item
    head = f"{item.path}  {_platform(item)}  {item.disc}  {item.size:,} bytes"
    marks = ("*", *(" " for _ in offer.targets[1:]))
    return [
        head,
        *(f"  {mark} {target.name}" for mark, target in zip(marks, offer.targets, strict=True)),
    ]


def offer_json(offer: Offer) -> Json:
    return {
        "path": str(offer.item.path),
        "platform": offer.item.platform,
        "disc": offer.item.disc.value,
        "size": offer.item.size,
        "default": offer.targets[0].name,
        "targets": [target.name for target in offer.targets],
    }


def _kept(plan: Plan, index: int) -> int:
    return plan.temporary // (len(plan.steps) - 1) if index < len(plan.steps) - 1 else 0


def plan_lines(plan: Plan) -> list[str]:
    steps = [
        f"  {index + 1}. {step.source} to {step.target}"
        + (
            f", kept in a temporary folder: {_kept(plan, index):,} bytes"
            if _kept(plan, index)
            else ""
        )
        for index, step in enumerate(plan.steps)
    ]
    return [
        f"{plan.item.path} to {plan.target.name}",
        *steps,
        f"  temporary space: {plan.temporary:,} bytes",
        f"  expected output: {plan.output:,} bytes",
    ]


def plan_json(plan: Plan) -> Json:
    steps = [
        {"from": step.source.value, "to": step.target.value, "temporary": _kept(plan, index)}
        for index, step in enumerate(plan.steps)
    ]
    return {
        "path": str(plan.item.path),
        "target": plan.target.name,
        "steps": steps,
        "temporary": plan.temporary,
        "output": plan.output,
    }
