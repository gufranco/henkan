from __future__ import annotations

import re
import tomllib
from pathlib import Path

from henkan.version import VERSION

ROOT = Path(__file__).resolve().parents[2]
SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+([-+].*)?$")


class TestTheVersion:
    def test_it_is_a_semantic_version(self):
        # Arrange
        pattern = SEMVER

        # Act
        found = pattern.match(VERSION)

        # Assert
        assert found is not None

    def test_the_package_reads_it_from_the_one_file_the_release_stamps(self):
        # Arrange
        manifest = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

        # Act
        source = manifest["tool"]["hatch"]["version"]["path"]

        # Assert
        assert source == "src/henkan/version.py"
        assert "version" in manifest["project"]["dynamic"]
