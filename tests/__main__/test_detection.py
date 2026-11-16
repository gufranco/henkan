from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from henkan.synthetic_test_support import (
    Tree,
    game_code,
    iso_image,
    ncch,
    ncsd,
    nintendo_header,
    npdm,
    patched,
    pbp_image,
    raw_image,
    rng,
    sfo,
    xdvdfs_volume,
)

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
LETTERS, DIGITS = game_code(rng())
CODE = f"{LETTERS}-{DIGITS}"
BOOT_NAME = f"{LETTERS}_{DIGITS[:3]}.{DIGITS[3:]};1"
PS1: Tree = {"SYSTEM.CNF;1": f"BOOT = cdrom:\\{BOOT_NAME}".encode()}
PS2: Tree = {"SYSTEM.CNF;1": f"BOOT2 = cdrom0:\\{BOOT_NAME}".encode()}
SECTORS = bytes(2048 * 20)
GDI = "3\n1 0 4 2352 track01.bin 0\n2 756 0 2352 track02.raw 0\n3 45000 4 2352 track03.bin 0\n"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "henkan", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(SRC)},
        check=False,
    )


def written(folder: Path, name: str, data: bytes) -> Path:
    path = folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def cue_set(folder: Path) -> Path:
    written(folder, "game.bin", raw_image(iso_image(PS1), 2))
    return written(folder, "game.cue", b'FILE "game.bin" BINARY\nTRACK 01 MODE2/2352\n')


def gdi_set(folder: Path) -> Path:
    for name in ("track01.bin", "track02.raw", "track03.bin"):
        written(folder, name, bytes(2352 * 2))
    return written(folder, "game.gdi", GDI.encode())


def switch_folder(folder: Path, gap: int) -> Path:
    written(folder, "exefs/main", b"code")
    written(folder, "exefs/main.npdm", npdm(0x0100ABCD12345000, gap))
    written(folder, "romfs/data.bin", b"data")
    return folder


def ps3_folder(folder: Path) -> Path:
    written(folder, "PS3_GAME/PARAM.SFO", sfo({"TITLE_ID": LETTERS + DIGITS}))
    return folder


PLATFORMS = {
    "PS1": cue_set,
    "PS2": lambda folder: written(folder, "game.iso", iso_image(PS2)),
    "PSP": lambda folder: written(folder, "game.iso", iso_image({"PSP_GAME": {}})),
    "PS3": ps3_folder,
    "Dreamcast": gdi_set,
    "Saturn": lambda folder: written(folder, "game.iso", patched(SECTORS, 0, b"SEGA SEGASATURN ")),
    "Sega CD": lambda folder: written(folder, "game.iso", patched(SECTORS, 0, b"SEGADISCSYSTEM  ")),
    "GameCube": lambda folder: written(
        folder, "game.iso", nintendo_header("ABCE01", "Lantern", wii=False) + SECTORS
    ),
    "Wii": lambda folder: written(
        folder, "game.iso", nintendo_header("ABCP01", "Lantern", wii=True) + SECTORS
    ),
    "Wii U": lambda folder: written(folder, "game.wud", b"WUP-P-ABCE" + SECTORS),
    "Xbox": lambda folder: written(folder, "game.iso", xdvdfs_volume(("default.xbe",))),
    "Xbox 360": lambda folder: written(folder, "game.iso", xdvdfs_volume(("default.xex",))),
    "Switch": lambda folder: switch_folder(folder / "Game", 0x200),
    "Switch 2": lambda folder: switch_folder(folder / "Game", 0x300),
    "3DS": lambda folder: written(folder, "game.3ds", ncsd(ncch(decrypted=True))),
}


class TestContentDecidesThePlatform:
    def test_a_ps2_dvd_iso_named_bin_is_reported_as_a_ps2_dvd_with_its_id(self, tmp_path):
        # Arrange
        path = tmp_path / "game.bin"
        with path.open("wb") as handle:
            handle.write(iso_image(PS2))
            handle.truncate(737_280_000 + 2048)

        # Act
        result = run("info", "--json", str(path))

        # Assert
        item = json.loads(result.stdout)["items"][0]
        assert result.returncode == 0
        assert (item["platform"], item["disc"], item["id"]) == ("PS2", "DVD", CODE)

    @pytest.mark.parametrize("platform", sorted(PLATFORMS))
    def test_info_names_every_platform_from_a_synthetic_image(self, tmp_path, platform):
        # Arrange
        path = PLATFORMS[platform](tmp_path)

        # Act
        result = run("info", "--json", str(path))

        # Assert
        items = json.loads(result.stdout)["items"]
        assert result.returncode == 0
        assert [item["platform"] for item in items] == [platform]

    @pytest.mark.parametrize("platform", sorted(PLATFORMS))
    def test_list_offers_every_platform_at_least_one_target(self, tmp_path, platform):
        # Arrange
        path = PLATFORMS[platform](tmp_path)

        # Act
        result = run("list", "--json", str(path))

        # Assert
        items = json.loads(result.stdout)["items"]
        assert result.returncode == 0
        assert [item["default"] in item["targets"] for item in items] == [True]

    def test_an_image_no_reader_recognizes_is_reported_without_a_platform(self, tmp_path):
        # Arrange
        path = written(tmp_path, "data.iso", SECTORS)

        # Act
        result = run("info", "--json", str(path))

        # Assert
        assert result.returncode == 0
        assert json.loads(result.stdout)["items"][0]["platform"] is None


class TestWhatIsNotADisc:
    def test_an_empty_file_is_refused_as_empty(self, tmp_path):
        # Arrange
        path = written(tmp_path, "empty.iso", b"")

        # Act
        result = run("info", str(path))

        # Assert
        assert (result.returncode, result.stderr) == (1, "refused: empty.iso is empty\n")

    def test_a_two_kibibyte_file_is_refused_as_too_small(self, tmp_path):
        # Arrange
        path = written(tmp_path, "small.iso", bytes(2048))

        # Act
        result = run("info", str(path))

        # Assert
        assert result.returncode == 1
        assert result.stderr == (
            "refused: small.iso is too small to be a disc image: 2048 bytes, when an image "
            "holds more than one sector of 2048 or 2352 bytes\n"
        )

    def test_a_cue_naming_missing_files_is_refused_with_their_names(self, tmp_path):
        # Arrange
        path = written(tmp_path, "game.cue", b'FILE "gone.bin" BINARY\nTRACK 01 MODE2/2352\n')

        # Act
        result = run("info", str(path))

        # Assert
        assert (result.returncode, result.stderr) == (
            1,
            "refused: game.cue names files that are missing: gone.bin\n",
        )


class TestOnlyWorkingConversionsAreOffered:
    def test_a_dreamcast_gdi_set_lists_chd_cdi_and_gdi_and_no_dvd_only_target(self, tmp_path):
        # Arrange
        path = gdi_set(tmp_path)

        # Act
        result = run("list", "--json", str(path))

        # Assert
        targets = json.loads(result.stdout)["items"][0]["targets"]
        assert result.returncode == 0
        assert targets == ["chd", "gdi", "cue", "cdi", "cue-ecc"]

    def test_a_pbp_to_cdi_dry_run_names_each_step_and_its_temporary_space(self, tmp_path):
        # Arrange
        image = pbp_image(1, {"DISC_ID": LETTERS + DIGITS})
        path = written(tmp_path, "game.pbp", image)

        # Act
        result = run("convert", str(path), "--to", "cdi", "--dry-run")

        # Assert
        size = len(image) * 8 // 5
        assert result.returncode == 0
        assert result.stdout.splitlines() == [
            f"{path} to cdi",
            f"  1. pbp to cue, kept in a temporary folder: {size:,} bytes",
            "  2. cue to cdi",
            f"  temporary space: {size:,} bytes",
            f"  expected output: {size:,} bytes",
        ]
