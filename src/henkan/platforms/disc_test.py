import pytest

from henkan.formats import sectors
from henkan.model import Platform
from henkan.platforms import disc
from henkan.platforms.identity import UNKNOWN, Identity
from henkan.source import memory_source
from henkan.synthetic_test_support import (
    Tree,
    game_code,
    iso_image,
    patched,
    raw_image,
    rng,
    sfo,
    udf_image,
)

LETTERS, DIGITS = game_code(rng())
CODE = f"{LETTERS}-{DIGITS}"
PS2: Tree = {"SYSTEM.CNF;1": f"BOOT2 = cdrom0:\\{LETTERS}_{DIGITS[:3]}.{DIGITS[3:]};1".encode()}
PS3: Tree = {"PS3_GAME": {"PARAM.SFO;1": sfo({"TITLE_ID": LETTERS + DIGITS})}}
SATURN = patched(bytes(20 * 2048), 0, b"SEGA SEGASATURN ")


class TestSniffingADisc:
    def test_a_cooked_iso_9660_volume_is_read_for_its_platform(self):
        # Arrange
        source = memory_source(iso_image(PS2))

        # Act
        found = disc.sniff(source)

        # Assert
        assert found == Identity(Platform.PS2, CODE)

    @pytest.mark.parametrize("mode", [1, 2])
    def test_a_raw_image_is_read_through_its_sector_layout(self, mode):
        # Arrange
        source = memory_source(raw_image(iso_image(PS2), mode))

        # Act
        found = disc.sniff(source)

        # Assert
        assert found == Identity(Platform.PS2, CODE)

    def test_a_udf_only_volume_is_read_when_no_iso_9660_descriptor_exists(self):
        # Arrange
        source = memory_source(udf_image({"SYSTEM.CNF": PS2["SYSTEM.CNF;1"]}))

        # Act
        found = disc.sniff(source)

        # Assert
        assert found == Identity(Platform.PS2, CODE)

    def test_the_base_moves_where_the_disc_starts(self):
        # Arrange
        source = memory_source(bytes(4704) + raw_image(iso_image(PS2), 2))

        # Act
        found = disc.sniff(source, 4704)

        # Assert
        assert found == Identity(Platform.PS2, CODE)

    def test_a_dreamcast_boot_sector_wins_over_any_volume(self):
        # Arrange
        source = memory_source(patched(iso_image(PS2), 0, b"SEGA SEGAKATANA "))

        # Act
        found = disc.sniff(source)

        # Assert
        assert found == Identity(Platform.DREAMCAST)

    def test_a_saturn_boot_sector_names_the_console_when_no_volume_does(self):
        # Arrange
        source = memory_source(SATURN)

        # Act
        found = disc.sniff(source)

        # Assert
        assert found == Identity(Platform.SATURN)

    def test_a_ps3_disc_is_found_on_a_cooked_iso_9660_image(self):
        # Arrange
        source = memory_source(iso_image(PS3))

        # Act
        found = disc.sniff(source)

        # Assert
        assert (found.platform, found.game_id) == (Platform.PS3, LETTERS + DIGITS)

    def test_a_ps3_folder_inside_a_raw_image_is_not_a_ps3_disc(self):
        # Arrange
        source = memory_source(raw_image(iso_image(PS3), 1))

        # Act
        found = disc.sniff(source)

        # Assert
        assert found == UNKNOWN

    @pytest.mark.parametrize(
        "image",
        [
            b"",
            bytes(40 * 2048),
            iso_image({"README.TXT;1": b"hello"}),
            patched(iso_image(PS2), 18 * 2048, b"\x05"),
        ],
    )
    def test_nothing_recognized_or_a_read_error_gives_no_platform(self, image):
        # Arrange
        source = memory_source(image)

        # Act
        found = disc.sniff(source)

        # Assert
        assert found == UNKNOWN


class TestFindingAVolume:
    def test_a_volume_is_found_through_the_layout_that_holds_it(self):
        # Arrange
        source = memory_source(iso_image(PS2))

        # Act
        found = disc.holds_volume(source)

        # Assert
        assert found is True

    def test_an_image_without_one_holds_none(self):
        # Arrange
        source = memory_source(SATURN)

        # Act
        found = disc.holds_volume(source)

        # Assert
        assert found is False

    def test_only_the_cooked_layout_is_tried(self):
        # Arrange
        source = memory_source(raw_image(iso_image(PS2), 1))

        # Act
        found = disc.holds_volume(source)

        # Assert
        assert (found, sectors.COOKED.stride) == (False, 2048)
