import pytest

from henkan.model import Platform
from henkan.platforms import nintendo
from henkan.platforms.identity import UNKNOWN, Identity
from henkan.source import memory_source
from henkan.synthetic_test_support import game_code, nintendo_header, rng, title

LETTERS, DIGITS = game_code(rng())
NAME = title(rng())


def code(region: str) -> str:
    return f"{LETTERS[:3]}{region}{DIGITS[:2]}"


class TestIdentifyingANintendoDisc:
    @pytest.mark.parametrize(
        ("wii", "platform"), [(True, Platform.WII), (False, Platform.GAMECUBE)]
    )
    def test_the_header_magic_names_the_console_and_carries_id_and_title(self, wii, platform):
        # Arrange
        source = memory_source(nintendo_header(code("E"), NAME, wii=wii))

        # Act
        found = nintendo.identify(source)

        # Assert
        assert found == Identity(platform, code("E"), NAME, "USA")

    @pytest.mark.parametrize(
        ("letter", "region"),
        [("P", "Europe"), ("J", "Japan"), ("K", "Korea"), ("Z", "")],
    )
    def test_the_fourth_character_of_the_id_names_the_region(self, letter, region):
        # Arrange
        source = memory_source(nintendo_header(code(letter), NAME, wii=True))

        # Act
        found = nintendo.identify(source)

        # Assert
        assert found.region == region

    def test_a_wii_u_disc_starts_with_its_product_prefix(self):
        # Arrange
        source = memory_source(b"WUP-P-" + LETTERS.encode() + bytes(64))

        # Act
        found = nintendo.identify(source)

        # Assert
        assert found == Identity(Platform.WII_U, LETTERS)

    @pytest.mark.parametrize("data", [bytes(0x60), b"WUP-P-AB", bytes(8)])
    def test_anything_else_is_unknown(self, data):
        # Arrange
        source = memory_source(data)

        # Act
        found = nintendo.identify(source)

        # Assert
        assert found == UNKNOWN
