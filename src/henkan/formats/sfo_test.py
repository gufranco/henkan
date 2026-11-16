import struct

import pytest
from hypothesis import given

from henkan.errors import FormatError
from henkan.formats import sfo
from henkan.fuzz_test_support import CUTS, FUZZ, MUTATIONS, attempt, corrupted, structure
from henkan.source import Source
from henkan.synthetic_test_support import game_code, patched, rng, title
from henkan.synthetic_test_support import sfo as build

LETTERS, DIGITS = game_code(rng())
NAME = title(rng())
VALUES = {"BOOTABLE": 1, "CATEGORY": "DG", "TITLE": NAME, "TITLE_ID": LETTERS + DIGITS}
IMAGE = build(VALUES)
HOT = structure(IMAGE)


def parse_source(source: Source) -> None:
    sfo.parse(source.read(0, source.size))


class TestParsingAParamSfo:
    def test_text_and_integer_entries_come_back_by_key(self):
        # Arrange
        data = IMAGE

        # Act
        values = sfo.parse(data)

        # Assert
        assert values == VALUES

    def test_text_stops_at_its_first_nul(self):
        # Arrange
        data = build({"TITLE": "Left\0Right"})

        # Act
        values = sfo.parse(data)

        # Assert
        assert values == {"TITLE": "Left"}


class TestRefusingWhatIsNotAParamSfo:
    @pytest.mark.parametrize(
        ("data", "reason"),
        [
            (b"\0PSF", "not a PARAM.SFO"),
            (patched(IMAGE, 0, b"\0PSX"), "not a PARAM.SFO"),
            (
                patched(IMAGE, 16, struct.pack("<I", 513)),
                "a PARAM.SFO with 513 entries passes the limit of 512",
            ),
            (patched(build({"A": 1}), 16, struct.pack("<I", 3)), "PARAM.SFO entry 1 is cut short"),
            (
                patched(IMAGE, 20 + 12, struct.pack("<I", 0x7FFFFFFF)),
                "PARAM.SFO entry 0 holds a number that is cut short",
            ),
        ],
    )
    def test_it_says_why(self, data, reason):
        # Arrange
        damaged = data

        # Act
        with pytest.raises(FormatError) as raised:
            sfo.parse(damaged)

        # Assert
        assert str(raised.value) == reason


class TestHostileInput:
    @FUZZ
    @given(mutations=MUTATIONS, cut=CUTS)
    def test_a_corrupted_file_is_refused_or_parsed_within_bounds(self, mutations, cut):
        # Arrange
        data = corrupted(IMAGE, HOT, mutations, cut)

        # Act
        outcome = attempt(parse_source, data)

        # Assert
        assert outcome.bounded
