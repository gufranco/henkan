import struct

import pytest
from hypothesis import given

from henkan.errors import FormatError
from henkan.formats import xdvdfs
from henkan.fuzz_test_support import CUTS, FUZZ, MUTATIONS, attempt, corrupted, structure
from henkan.source import Source, memory_source, open_source
from henkan.synthetic_test_support import patched, xdvdfs_volume

NAMES = ("default.xbe", "Media", "save.dat")
IMAGE = xdvdfs_volume(NAMES)
HOT = structure(IMAGE)
DESCRIPTOR = 0x10000
TABLE = DESCRIPTOR + 2048


def explore(source: Source) -> None:
    xdvdfs.read_volume(source).names()


class TestReadingAVolume:
    def test_a_trimmed_image_has_its_file_system_at_the_start(self):
        # Arrange
        source = memory_source(IMAGE)

        # Act
        volume = xdvdfs.read_volume(source)

        # Assert
        assert (volume.base, volume.names()) == (0, ("default.xbe", "Media", "save.dat"))

    @pytest.mark.parametrize("base", [0x0FD90000, 0x02080000, 0x18300000])
    def test_a_full_dump_has_its_file_system_at_a_known_base(self, tmp_path, base):
        # Arrange
        path = tmp_path / "dump.iso"
        with path.open("wb") as handle:
            handle.seek(base)
            handle.write(IMAGE)

        # Act
        with open_source(path) as source:
            volume = xdvdfs.read_volume(source)

        # Assert
        assert volume.base == base

    def test_an_entry_reached_twice_is_listed_once(self):
        # Arrange
        looping = patched(IMAGE, TABLE + 30, struct.pack("<H", 7))
        volume = xdvdfs.read_volume(memory_source(looping))

        # Act
        names = volume.names()

        # Assert
        assert names == ("default.xbe", "Media")

    def test_a_link_into_unused_table_space_adds_nothing(self):
        # Arrange
        padded = patched(IMAGE, TABLE + 48 + 2, struct.pack("<H", 25))
        volume = xdvdfs.read_volume(memory_source(padded))

        # Act
        names = volume.names()

        # Assert
        assert names == ("default.xbe", "Media", "save.dat")


class TestRefusingADamagedVolume:
    @pytest.mark.parametrize(
        "image",
        [
            bytes(0x11000),
            patched(IMAGE, DESCRIPTOR + 0x7EC, b"MICROSOFT*XBOX*MEDIX"),
            b"short",
        ],
    )
    def test_an_image_without_the_volume_descriptor(self, image):
        # Arrange
        source = memory_source(image, name="game.iso")

        # Act
        with pytest.raises(FormatError) as raised:
            xdvdfs.read_volume(source)

        # Assert
        assert str(raised.value) == "game.iso: no XDVDFS volume"

    def test_a_directory_table_over_the_limit(self):
        # Arrange
        image = patched(IMAGE, DESCRIPTOR + 0x18, struct.pack("<I", xdvdfs.TABLE_MAX + 1))
        volume = xdvdfs.read_volume(memory_source(image))

        # Act
        with pytest.raises(FormatError) as raised:
            volume.names()

        # Assert
        assert str(raised.value) == (
            "an XDVDFS directory of 268435457 bytes passes the limit of 268435456"
        )

    @pytest.mark.parametrize(
        ("offset", "damage"),
        [(TABLE + 2, struct.pack("<H", 0x1FF)), (DESCRIPTOR + 0x18, struct.pack("<I", 16))],
    )
    def test_an_entry_that_runs_past_its_table(self, offset, damage):
        # Arrange
        volume = xdvdfs.read_volume(memory_source(patched(IMAGE, offset, damage)))

        # Act
        with pytest.raises(FormatError) as raised:
            volume.names()

        # Assert
        assert str(raised.value) == "an XDVDFS directory entry runs past its table"


class TestHostileInput:
    @FUZZ
    @given(mutations=MUTATIONS, cut=CUTS)
    def test_a_corrupted_volume_is_refused_or_read_within_bounds(self, mutations, cut):
        # Arrange
        image = corrupted(IMAGE, HOT, mutations, cut)

        # Act
        outcome = attempt(explore, image)

        # Assert
        assert outcome.bounded
