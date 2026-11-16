from pathlib import Path

import pytest

from henkan import commands
from henkan.errors import UsageError
from henkan.gather import Refused
from henkan.model import Format, Platform
from henkan.routes import Step
from henkan.synthetic_test_support import game_code, iso_image, pbp_image, rng

LETTERS, DIGITS = game_code(rng())
PS2 = iso_image(
    {"SYSTEM.CNF;1": f"BOOT2 = cdrom0:\\{LETTERS}_{DIGITS[:3]}.{DIGITS[3:]};1".encode()}
)


def written(folder: Path, name: str, data: bytes) -> Path:
    path = folder / name
    path.write_bytes(data)
    return path


class TestInfo:
    def test_it_reports_each_item_and_each_refusal(self, tmp_path):
        # Arrange
        image = written(tmp_path, "game.iso", PS2)
        empty = written(tmp_path, "empty.iso", b"")

        # Act
        report = commands.info([image, empty])

        # Assert
        assert [(item.path, item.platform) for item in report.entries] == [(image, Platform.PS2)]
        assert report.refused == (Refused(empty, "empty.iso is empty"),)
        assert report.notes == ()


class TestOffers:
    def test_each_item_comes_with_the_targets_it_can_become(self, tmp_path):
        # Arrange
        image = written(tmp_path, "game.iso", PS2)

        # Act
        report = commands.offers([image])

        # Assert
        assert [
            (entry.item.path, [target.name for target in entry.targets]) for entry in report.entries
        ] == [(image, ["chd", "cso", "zso", "cso2"])]


class TestPlans:
    def test_each_item_gets_a_plan_for_the_named_target(self, tmp_path):
        # Arrange
        image = written(tmp_path, "game.iso", PS2)

        # Act
        report = commands.plans([image], "cso")

        # Assert
        assert [plan.steps for plan in report.entries] == [(Step(Format.ISO, Format.CSO),)]

    def test_without_a_target_each_item_takes_its_default(self, tmp_path):
        # Arrange
        image = written(tmp_path, "game.iso", PS2)

        # Act
        report = commands.plans([image], None)

        # Assert
        assert [plan.target.name for plan in report.entries] == ["chd"]

    def test_an_item_that_cannot_become_the_target_is_refused_beside_the_others(self, tmp_path):
        # Arrange
        image = written(tmp_path, "game.iso", PS2)
        packed = written(tmp_path, "game.pbp", pbp_image(1, {"DISC_ID": LETTERS + DIGITS}))

        # Act
        report = commands.plans([image, packed], "cdi")

        # Assert
        assert [plan.item.path for plan in report.entries] == [packed]
        assert report.refused == (
            Refused(image, "game.iso cannot become cdi; it can become: chd, cso, zso, cso2"),
        )

    def test_a_name_that_is_no_target_is_a_usage_error_before_any_file_is_read(self, tmp_path):
        # Arrange
        missing = tmp_path / "absent.iso"

        # Act
        with pytest.raises(UsageError) as raised:
            commands.plans([missing], "mp3")

        # Assert
        assert str(raised.value).startswith("'mp3' is not a target; the targets are: 3dsx, art, ")
