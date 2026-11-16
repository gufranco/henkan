import pytest

from henkan.model import Platform
from henkan.platforms import ps3
from henkan.platforms.identity import Identity
from henkan.synthetic_test_support import game_code, rng, sfo, title

LETTERS, DIGITS = game_code(rng())
NAME = title(rng())


def disc_sfo(third: str = "U", category: str = "DG") -> bytes:
    code = f"{LETTERS[:2]}{third}{LETTERS[3]}-{DIGITS}"
    return sfo({"CATEGORY": category, "TITLE": NAME, "TITLE_ID": code})


class TestReadingAParamSfo:
    @pytest.mark.parametrize(
        ("third", "region"),
        [
            ("U", "USA"),
            ("E", "Europe"),
            ("J", "Japan"),
            ("A", "Asia"),
            ("K", "Korea"),
            ("H", "Hong Kong"),
            ("X", ""),
        ],
    )
    def test_the_title_id_loses_its_dash_and_its_third_letter_names_the_region(self, third, region):
        # Arrange
        data = disc_sfo(third)

        # Act
        found = ps3.identity(data)

        # Assert
        code = f"{LETTERS[:2]}{third}{LETTERS[3]}{DIGITS}"
        assert found == Identity(Platform.PS3, code, NAME, region)

    def test_an_unreadable_file_still_names_the_console(self):
        # Arrange
        data = b"not a PARAM.SFO"

        # Act
        found = ps3.identity(data)

        # Assert
        assert found == Identity(Platform.PS3)


class TestADiscFolder:
    def test_a_folder_holding_ps3_game_and_its_param_sfo_is_one(self, tmp_path):
        # Arrange
        (tmp_path / "ps3_game").mkdir()
        (tmp_path / "ps3_game" / "Param.sfo").write_bytes(disc_sfo())

        # Act
        found = ps3.disc_folder(tmp_path)

        # Assert
        assert found == Identity(Platform.PS3, LETTERS[:2] + "U" + LETTERS[3] + DIGITS, NAME, "USA")

    @pytest.mark.parametrize("made", [(), ("PS3_GAME",)])
    def test_a_folder_missing_either_is_not(self, tmp_path, made):
        # Arrange
        for name in made:
            (tmp_path / name).mkdir()

        # Act
        found = ps3.disc_folder(tmp_path)

        # Assert
        assert found is None


class TestAPsnFolder:
    def test_a_param_sfo_beside_usrdir_with_a_category_other_than_disc_is_one(self, tmp_path):
        # Arrange
        (tmp_path / "USRDIR").mkdir()
        (tmp_path / "PARAM.SFO").write_bytes(disc_sfo(category="HG"))

        # Act
        found = ps3.psn_folder(tmp_path)

        # Assert
        assert found == Identity(Platform.PS3, LETTERS[:2] + "U" + LETTERS[3] + DIGITS, NAME, "USA")

    @pytest.mark.parametrize(
        ("folders", "data"),
        [
            ((), disc_sfo(category="HG")),
            (("USRDIR", "PS3_GAME"), disc_sfo(category="HG")),
            (("USRDIR",), disc_sfo(category="DG")),
            (("USRDIR",), sfo({"CATEGORY": "HG", "TITLE_ID": "abcd12345"})),
            (("USRDIR",), b"damaged"),
            (("USRDIR",), None),
        ],
    )
    def test_anything_else_is_not(self, tmp_path, folders, data):
        # Arrange
        for name in folders:
            (tmp_path / name).mkdir()
        if data is not None:
            (tmp_path / "PARAM.SFO").write_bytes(data)

        # Act
        found = ps3.psn_folder(tmp_path)

        # Assert
        assert found is None
