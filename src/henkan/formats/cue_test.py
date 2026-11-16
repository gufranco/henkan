import pytest
from hypothesis import given

from henkan.errors import FormatError
from henkan.formats import cue, sheet
from henkan.formats.sheet import Track, TrackType
from henkan.fuzz_test_support import CUTS, FUZZ, MUTATIONS, attempt, corrupted, structure
from henkan.source import Source

GAME = """\
REM a comment line
FILE "Game (Track 1).bin" BINARY
  TRACK 01 MODE2/2352
    INDEX 01 00:00:00
FILE "Game (Track 2).bin" BINARY
  TRACK 02 AUDIO
    INDEX 00 00:00:00
    INDEX 01 00:02:00
"""
SINGLE = """\
file game.bin binary
  track 01 mode1/2048
    index 01 00:00:00
  track 02 audio
    index 01 01:02:03
"""
BASE = GAME.encode()
HOT = structure(BASE)


def parse_source(source: Source) -> None:
    cue.parse(sheet.text(source))


class TestParsingACue:
    def test_each_file_and_track_is_read_with_its_type_and_start(self):
        # Arrange
        text = GAME

        # Act
        parsed = cue.parse(text)

        # Assert
        assert parsed.files == ("Game (Track 1).bin", "Game (Track 2).bin")
        assert parsed.tracks == (
            Track(1, TrackType.MODE2_2352, "Game (Track 1).bin", 0, 2352, 0),
            Track(2, TrackType.AUDIO, "Game (Track 2).bin", 150, 2352, 352_800),
        )

    def test_keywords_match_in_any_case_and_a_bare_name_ends_at_a_space(self):
        # Arrange
        text = SINGLE

        # Act
        parsed = cue.parse(text)

        # Assert
        assert parsed.files == ("game.bin",)
        assert parsed.tracks == (
            Track(1, TrackType.MODE1_2048, "game.bin", 0, 2048, 0),
            Track(2, TrackType.AUDIO, "game.bin", 4653, 2352, 10_943_856),
        )

    def test_a_type_chd_cannot_hold_has_no_kind_and_a_raw_stride(self):
        # Arrange
        text = 'FILE "a.bin" BINARY\nTRACK 01 CDI/2352\nINDEX 01 00:00:00\n'

        # Act
        parsed = cue.parse(text)

        # Assert
        assert parsed.tracks == (Track(1, None, "a.bin", 0, 2352, 0),)


class TestRefusingWhatIsNotACue:
    @pytest.mark.parametrize(
        ("text", "reason"),
        [
            ("REM nothing here\n", "not a CUE sheet: it names no file"),
            ('FILE "" BINARY\n', "a CUE FILE line names nothing"),
            ("TRACK 01 AUDIO\nFILE a.bin BINARY\n", "CUE track 1 comes before any FILE"),
            ("FILE a.bin BINARY\nTRACK 00 AUDIO\n", "CUE track 0 is outside 1 to 99"),
            ("FILE a.bin BINARY\nINDEX 01 00:00:00\n", "a CUE INDEX comes before any TRACK"),
            (
                "FILE a.bin BINARY\nTRACK 01 AUDIO\nINDEX 01 00:60:00\n",
                "CUE position 00:60:00 is not a time",
            ),
            (
                "FILE a.bin BINARY\nTRACK 01 AUDIO\nINDEX 01 00:00:75\n",
                "CUE position 00:00:75 is not a time",
            ),
        ],
    )
    def test_it_says_why(self, text, reason):
        # Arrange
        damaged = text

        # Act
        with pytest.raises(FormatError) as raised:
            cue.parse(damaged)

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
