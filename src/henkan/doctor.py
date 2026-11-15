from __future__ import annotations

import importlib
import platform
import sys
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from types import ModuleType

from henkan.version import VERSION

MIN_PYTHON = (3, 14)
CODECS = ("zlib", "bz2", "lzma", "compression.zstd")
SUPPORTED_SYSTEMS = ("Linux", "Darwin")
UNSUPPORTED = "untested: henkan supports Linux and macOS"
NO_VERDICT = "nothing was checked, so there is no verdict to give"

Importer = Callable[[str], ModuleType]


class CheckStatus(StrEnum):
    OK = "ok"
    WARNING = "warning"
    MISSING = "missing"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class Check:
    name: str
    status: CheckStatus
    detail: str


@dataclass(frozen=True, slots=True)
class DoctorReport:
    checks: tuple[Check, ...]

    @property
    def healthy(self) -> bool:
        if not self.checks:
            raise ValueError(NO_VERDICT)
        return all(check.status is not CheckStatus.FAILED for check in self.checks)


def _python(version: tuple[int, int, int]) -> Check:
    shown = ".".join(str(part) for part in version)
    if version[:2] < MIN_PYTHON:
        floor = ".".join(str(part) for part in MIN_PYTHON)
        return Check(
            "python", CheckStatus.FAILED, f"{shown}, older than {floor}, the oldest supported"
        )
    return Check("python", CheckStatus.OK, shown)


def _platform(system: str) -> Check:
    host = f"{system} {platform.machine()}"
    if system not in SUPPORTED_SYSTEMS:
        return Check("platform", CheckStatus.WARNING, f"{host}, {UNSUPPORTED}")
    return Check("platform", CheckStatus.OK, host)


def _codec(name: str, importer: Importer) -> Check:
    try:
        importer(name)
    except ModuleNotFoundError:
        detail = f"this Python was built without {name}, which henkan needs"
        return Check(name, CheckStatus.FAILED, detail)
    return Check(name, CheckStatus.OK, "available")


def diagnose(
    *,
    importer: Importer = importlib.import_module,
    python: tuple[int, int, int] | None = None,
    system: str | None = None,
) -> DoctorReport:
    running = python if python is not None else sys.version_info[:3]
    host = system if system is not None else platform.system()
    return DoctorReport(
        (
            Check("henkan", CheckStatus.OK, VERSION),
            _python(running),
            _platform(host),
            *(_codec(name, importer) for name in CODECS),
        )
    )
