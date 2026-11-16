from __future__ import annotations

import importlib
import platform
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from importlib import metadata
from types import ModuleType

from henkan.version import VERSION

MIN_PYTHON = (3, 14)
CODECS = ("zlib", "bz2", "lzma", "compression.zstd")
SUPPORTED_SYSTEMS = ("Linux", "Darwin")
UNSUPPORTED = "untested: henkan supports Linux and macOS"
NO_VERDICT = "nothing was checked, so there is no verdict to give"

DISTRIBUTION = "henkan"
CHDMAN = "chdman"
CHDMAN_TESTED = ((0, 285), (0, 289))
CHDMAN_TIMEOUT = 10.0
CHDMAN_BANNER = re.compile(r"manager (\d{1,4})\.(\d{1,4})")
CHDMAN_MISSING = "not found; CHD files need it: rom-tools in Homebrew, mame-tools on Ubuntu"
REQUIREMENT = re.compile(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
PINNED = re.compile(r"==\s*([^\s;,]+)")
EXTRA = re.compile(r"extra\s*==\s*[\"']([^\"']+)[\"']")

Importer = Callable[[str], ModuleType]


@dataclass(frozen=True, slots=True)
class Installed:
    version: str
    path: str


def requirements(distribution: str = DISTRIBUTION) -> Sequence[str]:
    try:
        return tuple(metadata.requires(distribution) or ())
    except metadata.PackageNotFoundError:
        return ()


def installed(name: str) -> Installed | None:
    try:
        found = metadata.distribution(name)
    except metadata.PackageNotFoundError:
        return None
    return Installed(found.version, str(found.locate_file("")).rstrip("/"))


def banner(path: str, *, timeout: float = CHDMAN_TIMEOUT) -> str:
    try:
        done = subprocess.run(  # noqa: S603
            [path], capture_output=True, text=True, timeout=timeout, check=False
        )
    except OSError, subprocess.TimeoutExpired:
        return ""
    return done.stdout + done.stderr


@dataclass(frozen=True, slots=True)
class Tools:
    executable: str = sys.executable
    requirements: Callable[[], Sequence[str]] = requirements
    installed: Callable[[str], Installed | None] = installed
    find: Callable[[str], str | None] = shutil.which
    banner: Callable[[str], str] = banner


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


def _python(version: tuple[int, int, int], executable: str) -> Check:
    shown = ".".join(str(part) for part in version) + f" at {executable}"
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


def _package(requirement: str, tools: Tools) -> Check:
    name = REQUIREMENT.match(requirement)
    label = name[1] if name else requirement
    found = tools.installed(label)
    pinned, extra = PINNED.search(requirement), EXTRA.search(requirement)
    if found is None and extra:
        return Check(label, CheckStatus.MISSING, f"not installed; the {extra[1]} extra provides it")
    if found is None:
        return Check(label, CheckStatus.FAILED, "not installed, and henkan needs it")
    where = f"{found.version} at {found.path}"
    if pinned and pinned[1] != found.version:
        return Check(label, CheckStatus.WARNING, f"{where}, tested with {pinned[1]}")
    return Check(label, CheckStatus.OK, where)


def _chdman(tools: Tools) -> Check:
    path = tools.find(CHDMAN)
    if path is None:
        return Check(CHDMAN, CheckStatus.MISSING, CHDMAN_MISSING)
    low, high = (".".join(str(part) for part in bound) for bound in CHDMAN_TESTED)
    version = CHDMAN_BANNER.search(tools.banner(path))
    if version is None:
        detail = f"{path}, version unreadable; tested with {low} to {high}"
        return Check(CHDMAN, CheckStatus.WARNING, detail)
    where = f"{version[1]}.{version[2]} at {path}"
    if CHDMAN_TESTED[0] <= (int(version[1]), int(version[2])) <= CHDMAN_TESTED[1]:
        return Check(CHDMAN, CheckStatus.OK, where)
    detail = f"{where}, outside the tested range {low} to {high}"
    return Check(CHDMAN, CheckStatus.WARNING, detail)


def diagnose(
    *,
    importer: Importer = importlib.import_module,
    python: tuple[int, int, int] | None = None,
    system: str | None = None,
    tools: Tools | None = None,
) -> DoctorReport:
    running = python if python is not None else sys.version_info[:3]
    host = system if system is not None else platform.system()
    probes = tools if tools is not None else Tools()
    return DoctorReport(
        (
            Check("henkan", CheckStatus.OK, VERSION),
            _python(running, probes.executable),
            _platform(host),
            *(_codec(name, importer) for name in CODECS),
            *(_package(requirement, probes) for requirement in probes.requirements()),
            _chdman(probes),
        )
    )
