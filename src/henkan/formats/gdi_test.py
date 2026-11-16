import pytest
from hypothesis import given

from henkan.errors import FormatError
from henkan.formats import gdi, sheet
from henkan.formats.sheet import Track, TrackType
from henkan.fuzz_test_support import CUTS, FUZZ, MUTATIONS, attempt, corrupted, structure
from henkan.source import Source

GAME = """\
3
1 0 4 2352 track01.bin 0
2 756 0 2352 "track 02.raw" 0
3 45000 4 2048 track03.iso 0
"""
BASE = GAME.replace("\n", "\r\n").encode()
HOT = structure(BASE)


def parse_source(source: Source) -> None:
    gdi.parse(sheet.text(source))


class TestParsingAGdi:
    def test_each_track_is_read_with_its_file_type_and_start(self):
        # Arrange
        text = GAME

        # Act
        parsed = gdi.parse(text)

        # Assert
        assert parsed.files == ("track01.bin", "track 02.raw", "track03.iso")
        assert parsed.tracks == (
            Track(1, TrackType.MODE1_2352, "track01.bin", 0, 2352, 0),
            Track(2, TrackType.AUDIO, "track 02.raw", 756, 2352, 0),
            Track(3, TrackType.MODE1_2048, "track03.iso", 45000, 2048, 0),
        )

    @pytest.mark.parametrize("line", ["1 0 4 2336 track01.bin 0", "1 0 2 2352 track01.bin 0"])
    def test_a_type_and_size_pair_outside_the_known_ones_has_no_kind(self, line):
        # Arrange
        text = f"1\n{line}\n"

        # Act
        parsed = gdi.parse(text)

        # Assert
        assert parsed.tracks[0].kind is None


class TestRefusingWhatIsNotAGdi:
    @pytest.mark.parametrize(
        ("text", "reason"),
        [
            ("", "not a GDI: its first line is not a track count"),
            ("three\n", "not a GDI: its first line is not a track count"),
            ("0\n", "not a GDI: it names no file"),
            ("1\n1 0 4 2352\n", "GDI line '1 0 4 2352' is not a track"),
            ("1\n0 0 4 2352 a.bin 0\n", "GDI track 0 is outside 1 to 99"),
        ],
    )
    def test_it_says_why(self, text, reason):
        # Arrange
        damaged = text

        # Act
        with pytest.raises(FormatError) as raised:
            gdi.parse(damaged)

        # Assert
        assert str(raised.value) == reason


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
