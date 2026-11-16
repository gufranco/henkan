import pytest
from hypothesis import given

from henkan.errors import FormatError
from henkan.formats import sheet, toc
from henkan.fuzz_test_support import CUTS, FUZZ, MUTATIONS, attempt, corrupted, structure
from henkan.source import Source

GAME = """\
CD_ROM_XA

TRACK MODE2_RAW
NO COPY
DATAFILE "game.bin" 00:10:00

TRACK AUDIO
FILE "music.bin" 00:10:00 00:30:00
file "game.bin" 0
"""
BASE = GAME.encode()
HOT = structure(BASE)


def parse_source(source: Source) -> None:
    toc.parse(sheet.text(source))


class TestParsingAToc:
    def test_every_named_file_is_listed_once_and_no_track_type_is_claimed(self):
        # Arrange
        text = GAME

        # Act
        parsed = toc.parse(text)

        # Assert
        assert parsed.files == ("game.bin", "music.bin")
        assert parsed.tracks == ()


class TestRefusingWhatIsNotAToc:
    @pytest.mark.parametrize("text", ["", "CD_ROM\nTRACK MODE1\n", "DATAFILE game.bin\n"])
    def test_a_sheet_that_names_no_quoted_file(self, text):
        # Arrange
        damaged = text

        # Act
        with pytest.raises(FormatError) as raised:
            toc.parse(damaged)

        # Assert
        assert str(raised.value) == "not a TOC sheet: it names no file"


class TestHostileInput:
    @FUZZ
    @given(mutations=MUTATIONS, cut=CUTS)
    def test_a_corrupted_sheet_is_refused_or_parsed_within_bounds(self, mutations, cut):
        # Arrange
        data = corrupted(BASE, HOT, mutations, cut)

        # Act
        outcome = attempt(parse_source, data)

        # Assert
        assert outcome.bounded
