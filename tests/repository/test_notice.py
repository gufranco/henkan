from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COLUMNS = ("Area", "Source", "License", "How it was used")


def rows(text: str) -> list[list[str]]:
    table = [line for line in text.splitlines() if line.startswith("|")]
    cells = [[cell.strip() for cell in line.strip("|").split("|")] for line in table]
    return [row for row in cells if not all(set(cell) <= {":", "-"} for cell in row)]


def gaps(table: list[list[str]]) -> list[str]:
    header, *body = table
    if tuple(header) != COLUMNS:
        return ["header"]
    return [row[1] or "unnamed row" for row in body if len(row) != len(COLUMNS) or "" in row]


class TestTheNoticeTable:
    def test_a_row_without_a_license_is_named(self):
        # Arrange
        text = (
            "| Area | Source | License | How it was used |\n"
            "|:--|:--|:--|:--|\n"
            "| CHD | chdman |  | ran |"
        )

        # Act
        found = gaps(rows(text))

        # Assert
        assert found == ["chdman"]

    def test_a_wrong_header_is_reported(self):
        # Arrange
        text = "| Source | License |\n|:--|:--|\n| a | MIT |"

        # Act
        found = gaps(rows(text))

        # Assert
        assert found == ["header"]

    def test_every_source_names_its_license_and_use(self):
        # Arrange
        text = (ROOT / "NOTICE.md").read_text(encoding="utf-8")

        # Act
        found = gaps(rows(text))

        # Assert
        assert found == []
