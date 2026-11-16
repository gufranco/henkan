import pytest
from hypothesis import given

from henkan.errors import FormatError
from henkan.formats import ccd, sheet
from henkan.formats.sheet import Track, TrackType
from henkan.fuzz_test_support import CUTS, FUZZ, MUTATIONS, attempt, corrupted, structure
from henkan.source import Source

HEAD = """\
[CloneCD]
Version=3
[Disc]
TocEntries=5
Sessions=1
[Session 1]
PreGapMode=2
"""
ENTRIES = """\
[Entry 0]
Point=0xa0
Control=0x04
PLBA=0
[Entry 1]
Point=0x02
Control=0x00
PLBA=1150
[Entry 2]
Point=1
Control=0x04
PLBA=0
"""
TRACKS = """\
[TRACK 2]
MODE=0
INDEX 0=1000
INDEX 1=1150
[TRACK 1]
MODE=2
INDEX 1=0
[TRACK 3]
MODE=1
INDEX 1=2000
[TRACK 4]
MODE=7
INDEX 1=3000
"""
BASE = (HEAD + ENTRIES + TRACKS).encode()
HOT = structure(BASE)


def parse_source(source: Source) -> None:
    ccd.parse(sheet.text(source), "game.img")


class TestParsingACcd:
    def test_track_sections_give_each_track_in_number_order(self):
        # Arrange
        text = HEAD + ENTRIES + TRACKS

        # Act
        parsed = ccd.parse(text, "game.img")

        # Assert
        assert parsed.files == ("game.img",)
        assert parsed.tracks == (
            Track(1, TrackType.MODE2_2352, "game.img", 0, 2352, 0),
            Track(2, TrackType.AUDIO, "game.img", 1150, 2352, 2_704_800),
            Track(3, TrackType.MODE1_2352, "game.img", 2000, 2352, 4_704_000),
            Track(4, None, "game.img", 3000, 2352, 7_056_000),
        )

    def test_without_track_sections_the_table_of_contents_gives_the_tracks(self):
        # Arrange
        text = HEAD + ENTRIES

        # Act
        parsed = ccd.parse(text, "game.img")

        # Assert
        assert parsed.tracks == (
            Track(1, None, "game.img", 0, 2352, 0),
            Track(2, TrackType.AUDIO, "game.img", 1150, 2352, 2_704_800),
        )

    def test_lines_outside_any_section_are_ignored(self):
        # Arrange
        text = "stray=1\n; note\n" + HEAD + "[TRACK 1]\nMODE=2\nINDEX 1=0\n"

        # Act
        parsed = ccd.parse(text, "game.img")

        # Assert
        assert parsed.tracks == (Track(1, TrackType.MODE2_2352, "game.img", 0, 2352, 0),)


class TestRefusingWhatIsNotACcd:
    @pytest.mark.parametrize(
        ("text", "reason"),
        [
            ("[Disc]\nSessions=2\n", "a CCD with 2 sessions; henkan reads one"),
            (HEAD, "not a CCD: it names no track"),
            (HEAD + "[TRACK 1]\nINDEX 1=0\n", "CCD track 1 has no mode or no start"),
            (HEAD + "[TRACK 1]\nMODE=2\n", "CCD track 1 has no mode or no start"),
            (HEAD + "[TRACK 0]\nMODE=2\nINDEX 1=0\n", "CCD track 0 is outside 1 to 99"),
            (HEAD + "[TRACK 1]\nMODE=two\nINDEX 1=0\n", "CCD value 'two' is not a number"),
            (HEAD + "[TRACK 1]\nMODE=2\nINDEX 1=-5\n", "CCD track 1 starts before the disc"),
            (HEAD + "[Entry 0]\nPoint=1\nControl=4\n", "CCD track 1 has no mode or no start"),
        ],
    )
    def test_it_says_why(self, text, reason):
        # Arrange
        damaged = text

        # Act
        with pytest.raises(FormatError) as raised:
            ccd.parse(damaged, "game.img")

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
