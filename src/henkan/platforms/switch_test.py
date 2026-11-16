from pathlib import Path

import pytest

from henkan.errors import RefusalError
from henkan.model import Platform
from henkan.platforms import switch
from henkan.synthetic_test_support import npdm

TITLE = 0x0100ABCD12345000
TITLE_TEXT = "0100ABCD12345000"
SWITCH_1 = npdm(TITLE, 0x200)
SWITCH_2 = npdm(TITLE, 0x300)


def package(folder: Path, meta: bytes | None = SWITCH_1) -> None:
    (folder / "exefs").mkdir(parents=True)
    (folder / "romfs").mkdir()
    (folder / "exefs" / "main").write_bytes(b"code")
    if meta is not None:
        (folder / "exefs" / "main.npdm").write_bytes(meta)


class TestAPlainGameFolder:
    @pytest.mark.parametrize(
        ("meta", "platform"), [(SWITCH_1, Platform.SWITCH), (SWITCH_2, Platform.SWITCH_2)]
    )
    def test_main_npdm_gives_the_title_id_and_the_generation(self, tmp_path, meta, platform):
        # Arrange
        package(tmp_path, meta)

        # Act
        found = switch.detect(tmp_path)

        # Assert
        assert found == switch.SwitchFolder(platform, True, TITLE_TEXT, 0, 0)

    def test_an_aci0_block_away_from_its_recorded_place_is_found_by_search(self, tmp_path):
        # Arrange
        moved = bytearray(SWITCH_1)
        moved[0x70:0x74] = (0x400).to_bytes(4, "little")
        package(tmp_path, bytes(moved))

        # Act
        found = switch.detect(tmp_path)

        # Assert
        assert found == switch.SwitchFolder(Platform.SWITCH, True, TITLE_TEXT, 0, 0)

    def test_without_main_npdm_the_folder_name_gives_the_title_id(self, tmp_path):
        # Arrange
        folder = tmp_path / "Game [0100abcd12345000]"
        package(folder, None)

        # Act
        found = switch.detect(folder)

        # Assert
        assert found == switch.SwitchFolder(Platform.SWITCH, False, TITLE_TEXT, 0, 0)

    @pytest.mark.parametrize("meta", [npdm(TITLE, 0x280), b"META" + bytes(8)])
    def test_a_main_npdm_that_tells_no_generation_is_marked_uncertain(self, tmp_path, meta):
        # Arrange
        folder = tmp_path / TITLE_TEXT
        package(folder, meta)

        # Act
        found = switch.detect(folder)

        # Assert
        assert found == switch.SwitchFolder(Platform.SWITCH, False, TITLE_TEXT, 0, 0)

    @pytest.mark.parametrize("meta", [None, b"META" + bytes(0x70), b"junk"])
    def test_no_title_id_anywhere_is_refused_with_how_to_name_the_folder(self, tmp_path, meta):
        # Arrange
        folder = tmp_path / "Game"
        package(folder, meta)

        # Act
        with pytest.raises(RefusalError) as raised:
            switch.detect(folder)

        # Assert
        assert str(raised.value) == (
            "Game: no title ID in main.npdm or in the folder name; name the folder with the "
            "16-digit title ID, for example `Game [0100000000010000]`"
        )

    @pytest.mark.parametrize("made", [("exefs",), ("romfs",), ("exefs", "romfs")])
    def test_a_folder_missing_a_part_is_not_a_game_folder(self, tmp_path, made):
        # Arrange
        for name in made:
            (tmp_path / name).mkdir()

        # Act
        found = switch.detect(tmp_path)

        # Assert
        assert found is None


class TestAPackagedLayout:
    def test_base_updates_and_extra_content_are_counted(self, tmp_path):
        # Arrange
        package(tmp_path / "base")
        package(tmp_path / "updates" / "65536")
        package(tmp_path / "updates" / "131072")
        (tmp_path / "updates" / "notes").mkdir()
        (tmp_path / "updates" / "196608" / "romfs").mkdir(parents=True)
        (tmp_path / "dlc" / "0100ABCD12346001" / "0" / "romfs").mkdir(parents=True)
        (tmp_path / "dlc" / "0100ABCD12346001" / "0" / "romfs" / "data.bin").write_bytes(b"x")
        (tmp_path / "dlc" / "readme").mkdir()

        # Act
        found = switch.detect(tmp_path)

        # Assert
        assert found == switch.SwitchFolder(Platform.SWITCH, True, TITLE_TEXT, 2, 1)

    def test_a_base_alone_has_no_updates_and_no_extra_content(self, tmp_path):
        # Arrange
        package(tmp_path / "base")
        (tmp_path / "updates").write_bytes(b"a file, not a folder")

        # Act
        found = switch.detect(tmp_path)

        # Assert
        assert found == switch.SwitchFolder(Platform.SWITCH, True, TITLE_TEXT, 0, 0)

    def test_a_base_folder_without_files_is_not_a_packaged_layout(self, tmp_path):
        # Arrange
        (tmp_path / "base" / "exefs").mkdir(parents=True)

        # Act
        found = switch.detect(tmp_path)

        # Assert
        assert found is None
