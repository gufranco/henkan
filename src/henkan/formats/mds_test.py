import struct

import pytest
from hypothesis import given

from henkan.errors import FormatError
from henkan.formats import mds
from henkan.formats.sheet import Track, TrackType
from henkan.fuzz_test_support import CUTS, FUZZ, MUTATIONS, attempt, corrupted, structure
from henkan.source import memory_source
from henkan.synthetic_test_support import MdsTrack, mds_image, patched

LEAD_IN = MdsTrack(mode=0xAA, point=0xA0, stride=0, start=0, offset=0)
TRACKS = (
    LEAD_IN,
    MdsTrack(mode=0xA9, point=2, stride=2352, start=1150, offset=2_704_800),
    MdsTrack(mode=0xAB, point=1, stride=2352, start=0, offset=0),
)
IMAGE = mds_image(TRACKS, "*.mdf")
HOT = structure(IMAGE)
BLOCKS_AT = 0x70


def parsed(image: bytes) -> mds.Sheet:
    return mds.parse(memory_source(image, name="game.mds"))


class TestParsingAnMds:
    def test_track_blocks_give_each_track_and_lead_in_entries_are_skipped(self):
        # Arrange
        image = IMAGE

        # Act
        sheet = parsed(image)

        # Assert
        assert sheet.files == ("*.mdf",)
        assert sheet.tracks == (
            Track(1, None, "*.mdf", 0, 2352, 0),
            Track(2, TrackType.AUDIO, "*.mdf", 1150, 2352, 2_704_800),
        )

    def test_a_wide_file_name_is_read_as_sixteen_bit_text(self):
        # Arrange
        image = mds_image(TRACKS, "ゲーム.mdf", wide=True)

        # Act
        sheet = parsed(image)

        # Assert
        assert sheet.files == ("ゲーム.mdf",)


class TestNamingTheDataFile:
    @pytest.mark.parametrize(
        ("recorded", "expected"),
        [
            ("*.mdf", ("game.mdf", "game.img")),
            ("*.bin", ("game.bin", "game.mdf", "game.img")),
            ("C:\\discs\\other.mdf", ("other.mdf", "game.mdf", "game.img")),
            ("sub/dir/", ("game.mdf", "game.img")),
        ],
    )
    def test_the_recorded_name_comes_first_then_the_stem_with_each_extension(
        self, recorded, expected
    ):
        # Arrange
        stem = "game"

        # Act
        names = mds.candidates(recorded, stem)

        # Assert
        assert names == expected


class TestRefusingWhatIsNotAnMds:
    @pytest.mark.parametrize(
        ("image", "reason"),
        [
            (patched(IMAGE, 0, b"MEDIA DESCRIPTOX"), "game.mds: not an MDS descriptor"),
            (patched(IMAGE, 16, b"\x02"), "game.mds: MDS version 2 is not one henkan reads"),
            (
                patched(IMAGE, 0x14, struct.pack("<H", 3)),
                "game.mds: an MDS with 3 sessions; henkan reads one",
            ),
            (mds_image((LEAD_IN,), "*.mdf"), "game.mds: an MDS with no tracks"),
            (
                mds_image((MdsTrack(0xAB, 1, 2352, 0, 0, files=2),), "*.mdf"),
                "game.mds: track 1 spans 2 data files; henkan reads one",
            ),
            (
                mds_image((MdsTrack(0xAB, 1, 2000, 0, 0),), "*.mdf"),
                "game.mds: track 1 has 2000-byte sectors, which henkan does not read",
            ),
            (mds_image(TRACKS, ""), "game.mds: the MDS names no data file"),
            (
                patched(IMAGE, 0x50, struct.pack("<I", 0x7FFFFFF0)),
                "game.mds: 24 bytes at offset 2147483632 fall outside its 367 bytes",
            ),
        ],
    )
    def test_it_says_why(self, image, reason):
        # Arrange
        damaged = image

        # Act
        with pytest.raises(FormatError) as raised:
            parsed(damaged)

        # Assert
        assert str(raised.value) == reason


class TestHostileInput:
    @FUZZ
    @given(mutations=MUTATIONS, cut=CUTS)
    def test_a_corrupted_descriptor_is_refused_or_parsed_within_bounds(self, mutations, cut):
        # Arrange
        image = corrupted(IMAGE, HOT, mutations, cut)

        # Act
        outcome = attempt(mds.parse, image)

        # Assert
        assert outcome.bounded
