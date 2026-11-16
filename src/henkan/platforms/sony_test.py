import pytest

from henkan.formats import iso9660, sectors
from henkan.model import Platform
from henkan.platforms import sony
from henkan.platforms.identity import UNKNOWN, Identity
from henkan.source import memory_source
from henkan.synthetic_test_support import Tree, game_code, iso_image, rng, sfo, title

LETTERS, DIGITS = game_code(rng())
NAME = title(rng())
CODE = f"{LETTERS}-{DIGITS}"
PARAM = sfo({"CATEGORY": "DG", "TITLE": NAME, "TITLE_ID": f"{LETTERS[:2]}E{LETTERS[3]}-{DIGITS}"})


def volume(tree: Tree) -> iso9660.IsoVolume:
    view = sectors.SectorView(memory_source(iso_image(tree)), sectors.COOKED)
    return iso9660.read_volume(view)


def boot(line: str) -> Tree:
    return {"SYSTEM.CNF;1": line.encode() + b"\r\nVER = 1.00\r\n"}


class TestIdentifyingASonyDisc:
    @pytest.mark.parametrize(
        "line",
        [
            f"BOOT2 = cdrom0:\\{LETTERS}_{DIGITS[:3]}.{DIGITS[3:]};1",
            f"boot2=cdrom0:{LETTERS.lower()}-{DIGITS[:3]}{DIGITS[3:]}",
            f"BOOT2 = cdrom0:\\DIR/SUB\\{LETTERS}{DIGITS};1",
        ],
    )
    def test_a_boot2_line_means_ps2_and_gives_the_id(self, line):
        # Arrange
        disc = volume(boot(line))

        # Act
        found = sony.identify(disc, ps3=True)

        # Assert
        assert found == Identity(Platform.PS2, CODE)

    def test_a_boot_line_means_ps1_and_gives_the_id(self):
        # Arrange
        disc = volume(boot(f"BOOT = cdrom:\\{LETTERS}_{DIGITS[:3]}.{DIGITS[3:]};1"))

        # Act
        found = sony.identify(disc, ps3=True)

        # Assert
        assert found == Identity(Platform.PS1, CODE)

    @pytest.mark.parametrize(
        ("line", "platform"),
        [
            ("BOOT2 = cdrom0:\\GAME.ELF;1", Platform.PS2),
            ("BOOT = cdrom:\\GAME.EXE;1", Platform.PS1),
        ],
    )
    def test_a_boot_line_without_a_game_code_still_names_the_console(self, line, platform):
        # Arrange
        disc = volume(boot(line))

        # Act
        found = sony.identify(disc, ps3=True)

        # Assert
        assert found == Identity(platform)

    @pytest.mark.parametrize("name", ["PSP_GAME", "UMD_DATA.BIN;1"])
    def test_a_psp_marker_in_the_root_means_psp(self, name):
        # Arrange
        tree: Tree = {name: {} if name == "PSP_GAME" else b"ULJS"}
        disc = volume(tree)

        # Act
        found = sony.identify(disc, ps3=True)

        # Assert
        assert found == Identity(Platform.PSP)

    def test_a_ps3_game_folder_means_ps3_and_its_param_sfo_gives_the_rest(self):
        # Arrange
        disc = volume({"PS3_GAME": {"PARAM.SFO;1": PARAM}})

        # Act
        found = sony.identify(disc, ps3=True)

        # Assert
        code = f"{LETTERS[:2]}E{LETTERS[3]}{DIGITS}"
        assert found == Identity(Platform.PS3, code, NAME, "Europe")

    def test_a_ps3_game_folder_without_a_param_sfo_still_means_ps3(self):
        # Arrange
        disc = volume({"PS3_GAME": {"OTHER.BIN;1": b"x"}})

        # Act
        found = sony.identify(disc, ps3=True)

        # Assert
        assert found == Identity(Platform.PS3)

    def test_ps3_is_left_out_when_the_caller_rules_it_out(self):
        # Arrange
        disc = volume({"PS3_GAME": {"PARAM.SFO;1": PARAM}})

        # Act
        found = sony.identify(disc, ps3=False)

        # Assert
        assert found == UNKNOWN

    @pytest.mark.parametrize("tree", [{"README.TXT;1": b"hello"}, boot("VMODE = NTSC")])
    def test_a_volume_without_any_marker_is_unknown(self, tree):
        # Arrange
        disc = volume(tree)

        # Act
        found = sony.identify(disc, ps3=True)

        # Assert
        assert found == UNKNOWN
