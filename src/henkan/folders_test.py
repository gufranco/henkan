from pathlib import Path

import pytest

from henkan import folders
from henkan.errors import UnsupportedError
from henkan.model import DiscClass, Format, Item, Platform, Trait
from henkan.synthetic_test_support import game_code, npdm, rng, sfo, title

LETTERS, DIGITS = game_code(rng())
NAME = title(rng())
TITLE_TEXT = "0100ABCD12345000"
OVERHEAD = 4 * 0x10000


def switch_folder(folder: Path, meta: bytes) -> Path:
    (folder / "exefs").mkdir(parents=True)
    (folder / "romfs").mkdir()
    (folder / "exefs" / "main").write_bytes(bytes(100))
    (folder / "exefs" / "main.npdm").write_bytes(meta)
    return folder


class TestASwitchFolder:
    def test_it_reports_generation_title_id_and_what_it_holds(self, tmp_path):
        # Arrange
        folder = switch_folder(tmp_path / "Game", npdm(int(TITLE_TEXT, 16), 0x300))

        # Act
        item = folders.analyze(folder)

        # Assert
        assert item == Item(
            path=folder,
            kind=Format.FOLDER,
            platform=Platform.SWITCH_2,
            disc=DiscClass.DVD,
            reason=(
                "a decrypted Switch 2 game folder: 1 game, 0 updates, 0 extra content, 2 files"
            ),
            tracks=(),
            size=100 + 0x700,
            files=(folder,),
            game_id=TITLE_TEXT,
            traits=frozenset({Trait.HEURISTIC}),
        )

    def test_a_generation_main_npdm_does_not_tell_is_taken_as_switch_with_a_warning(self, tmp_path):
        # Arrange
        folder = switch_folder(tmp_path / TITLE_TEXT, b"META" + bytes(8))

        # Act
        item = folders.analyze(folder)

        # Assert
        assert (item.platform, item.warnings) == (
            Platform.SWITCH,
            ("main.npdm does not tell Switch from Switch 2, so this is taken as Switch",),
        )


class TestAPs3Folder:
    def test_a_disc_folder_is_ps3_with_its_id_title_and_region(self, tmp_path):
        # Arrange
        (tmp_path / "PS3_GAME").mkdir()
        code = f"{LETTERS[:2]}J{LETTERS[3]}{DIGITS}"
        (tmp_path / "PS3_GAME" / "PARAM.SFO").write_bytes(sfo({"TITLE": NAME, "TITLE_ID": code}))

        # Act
        item = folders.analyze(tmp_path)

        # Assert
        assert (item.kind, item.platform, item.disc, item.game_id, item.title, item.region) == (
            Format.FOLDER,
            Platform.PS3,
            DiscClass.DVD,
            code,
            NAME,
            "Japan",
        )
        assert (item.size, item.traits) == (
            OVERHEAD + len(sfo({"TITLE": NAME, "TITLE_ID": code})),
            frozenset(),
        )

    def test_a_psn_folder_carries_the_psn_trait(self, tmp_path):
        # Arrange
        (tmp_path / "USRDIR").mkdir()
        code = LETTERS + DIGITS
        (tmp_path / "PARAM.SFO").write_bytes(sfo({"CATEGORY": "HG", "TITLE_ID": code}))

        # Act
        item = folders.analyze(tmp_path)

        # Assert
        assert (item.platform, item.game_id, item.traits) == (
            Platform.PS3,
            code,
            frozenset({Trait.PSN}),
        )


class TestAnXboxFolder:
    @pytest.mark.parametrize(
        ("name", "platform"), [("default.xex", Platform.XBOX_360), ("default.xbe", Platform.XBOX)]
    )
    def test_its_boot_file_names_the_console(self, tmp_path, name, platform):
        # Arrange
        (tmp_path / name).write_bytes(bytes(64))

        # Act
        item = folders.analyze(tmp_path)

        # Assert
        assert (item.kind, item.platform, item.disc, item.size) == (
            Format.FOLDER,
            platform,
            DiscClass.DVD,
            64 + OVERHEAD,
        )


class TestAnyOtherFolder:
    def test_it_is_refused_with_what_was_looked_for(self, tmp_path):
        # Arrange
        folder = tmp_path / "photos"
        folder.mkdir()

        # Act
        with pytest.raises(UnsupportedError) as raised:
            folders.analyze(folder)

        # Assert
        assert str(raised.value) == (
            "photos is not a recognized Switch, PS3, Xbox or Xbox 360 game folder: it has no "
            "exefs beside romfs, no PS3_GAME, no PARAM.SFO beside USRDIR, no default.xex and no "
            "default.xbe at its top"
        )
