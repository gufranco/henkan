import struct

import pytest
from hypothesis import given

from henkan.errors import FormatError
from henkan.formats import pbp
from henkan.fuzz_test_support import CUTS, FUZZ, MUTATIONS, attempt, corrupted, structure
from henkan.source import memory_source
from henkan.synthetic_test_support import game_code, patched, pbp_image, rng

LETTERS, DIGITS = game_code(rng())
VALUES = {"CATEGORY": "ME", "DISC_ID": (LETTERS + DIGITS).lower()}
SINGLE = pbp_image(1, VALUES)
HOT = structure(SINGLE)
PSAR = 0x10000


def opened(image: bytes) -> pbp.Pbp:
    return pbp.read(memory_source(image, name="game.pbp"))


class TestReadingAPbp:
    def test_a_single_disc_file_holds_one_disc_and_its_id_in_capitals(self):
        # Arrange
        image = SINGLE

        # Act
        found = opened(image)

        # Assert
        assert found == pbp.Pbp(1, LETTERS + DIGITS)

    @pytest.mark.parametrize("discs", [2, 5])
    def test_a_multi_disc_file_counts_its_used_disc_slots(self, discs):
        # Arrange
        image = pbp_image(discs, VALUES)

        # Act
        found = opened(image)

        # Assert
        assert found.discs == discs


class TestRefusingWhatIsNotAPs1Pbp:
    @pytest.mark.parametrize(
        ("image", "reason"),
        [
            (patched(SINGLE, 0, b"\0PBX"), "game.pbp: not a PBP"),
            (
                patched(SINGLE, PSAR, b"NPUMDIMG"),
                "game.pbp: a PBP that holds no PS1 game",
            ),
            (
                patched(pbp_image(2, VALUES), PSAR + 0x200, bytes(20)),
                "game.pbp: a multi-disc PBP that lists no disc",
            ),
            (
                patched(SINGLE, 12, struct.pack("<I", 8)),
                "game.pbp: the PBP header is damaged",
            ),
            (
                patched(SINGLE, 12, struct.pack("<I", 0x7FFFFFFF)),
                "game.pbp: the PBP header is damaged",
            ),
        ],
    )
    def test_it_says_why(self, image, reason):
        # Arrange
        damaged = image

        # Act
        with pytest.raises(FormatError) as raised:
            opened(damaged)

        # Assert
        assert str(raised.value) == reason


class TestHostileInput:
    @FUZZ
    @given(mutations=MUTATIONS, cut=CUTS)
    def test_a_corrupted_file_is_refused_or_read_within_bounds(self, mutations, cut):
        # Arrange
        image = corrupted(SINGLE, HOT, mutations, cut)

        # Act
        outcome = attempt(pbp.read, image)

        # Assert
        assert outcome.bounded
