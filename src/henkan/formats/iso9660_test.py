import struct

import pytest
from hypothesis import given

from henkan.errors import FormatError
from henkan.formats import iso9660, sectors
from henkan.formats.volume import find
from henkan.fuzz_test_support import CUTS, FUZZ, MUTATIONS, attempt, corrupted, structure
from henkan.source import Source, memory_source
from henkan.synthetic_test_support import iso_image, iso_record, patched, raw_image

TREE = {
    "SYSTEM.CNF;1": b"BOOT2 = cdrom0:\\SLUS_123.45;1\r\n",
    "README.;1": b"plain",
    "DATA": {"LEVEL.BIN;1": bytes(range(256)) * 9},
}
IMAGE = iso_image(TREE, label="HENKAN")
HOT = structure(IMAGE)
ROOT_AT = 18 * sectors.SECTOR
MANY = {f"FILE{index:03}.BIN;1": b"" for index in range(60)}


def opened(image: bytes, layout: sectors.Layout = sectors.COOKED) -> iso9660.IsoVolume:
    return iso9660.read_volume(sectors.SectorView(memory_source(image, name="disc.iso"), layout))


def explore(source: Source) -> None:
    volume = iso9660.read_volume(sectors.SectorView(source, sectors.COOKED))
    for entry in volume.root():
        if entry.directory:
            volume.children(entry)
        else:
            volume.read(entry, 64)


class TestReadingAVolume:
    def test_the_root_lists_names_without_version_or_trailing_dot(self):
        # Arrange
        volume = opened(IMAGE)

        # Act
        entries = volume.root()

        # Assert
        assert [(entry.name, entry.directory) for entry in entries] == [
            ("SYSTEM.CNF", False),
            ("README", False),
            ("DATA", True),
        ]

    def test_the_label_and_size_come_from_the_descriptor(self):
        # Arrange
        image = IMAGE

        # Act
        volume = opened(image)

        # Assert
        assert (volume.label, volume.sectors) == ("HENKAN", len(IMAGE) // 2048)

    @pytest.mark.parametrize(("layout", "mode"), [(sectors.RAW_MODE1, 1), (sectors.RAW_MODE2, 2)])
    def test_a_raw_image_reads_through_its_layout(self, layout, mode):
        # Arrange
        volume = opened(raw_image(IMAGE, mode), layout)
        entry = find(volume.root(), "system.cnf")

        # Act
        data = volume.read(entry, 5)

        # Assert
        assert data == b"BOOT2"

    def test_a_subdirectory_lists_its_own_files(self):
        # Arrange
        volume = opened(IMAGE)
        directory = volume.root()[2]

        # Act
        entries = volume.children(directory)

        # Assert
        assert [(entry.name, entry.size) for entry in entries] == [("LEVEL.BIN", 2304)]

    def test_a_file_reads_no_further_than_its_size(self):
        # Arrange
        volume = opened(IMAGE)
        entry = volume.root()[1]

        # Act
        data = volume.read(entry, 4096)

        # Assert
        assert data == b"plain"

    def test_a_directory_spanning_sectors_skips_the_padding_between_them(self):
        # Arrange
        volume = opened(iso_image(MANY))

        # Act
        entries = volume.root()

        # Assert
        assert [entry.name for entry in entries] == [f"FILE{index:03}.BIN" for index in range(60)]


class TestRefusingADamagedVolume:
    def test_a_file_has_no_children(self):
        # Arrange
        volume = opened(IMAGE)
        entry = volume.root()[0]

        # Act
        with pytest.raises(FormatError) as raised:
            volume.children(entry)

        # Assert
        assert str(raised.value) == "'SYSTEM.CNF' is a file, not a directory"

    def test_a_directory_over_the_limit_is_refused_before_it_is_read(self):
        # Arrange
        record = iso_record(b"\0", 18, 1024 * 1024 + 1, directory=True)
        volume = opened(patched(IMAGE, 16 * 2048 + 156, record))

        # Act
        with pytest.raises(FormatError) as raised:
            volume.root()

        # Assert
        assert str(raised.value) == "a directory of 1048577 bytes passes the limit of 1048576"

    @pytest.mark.parametrize(
        ("offset", "damage"),
        [
            (ROOT_AT + 68, bytes((33,))),
            (ROOT_AT + 68, struct.pack("<B31xB", 34, 200)),
            (16 * 2048 + 156, iso_record(b"\0", 18, 100, directory=True)),
        ],
    )
    def test_a_damaged_directory_record_is_a_format_error(self, offset, damage):
        # Arrange
        volume = opened(patched(IMAGE, offset, damage))

        # Act
        with pytest.raises(FormatError) as raised:
            volume.root()

        # Assert
        assert str(raised.value) == "a directory record at byte 68 is damaged"

    @pytest.mark.parametrize("damage", [b"\x02CD001", b"\x01CD002"])
    def test_a_sector_sixteen_that_is_no_primary_descriptor_is_a_format_error(self, damage):
        # Arrange
        image = patched(IMAGE, 16 * 2048, damage)

        # Act
        with pytest.raises(FormatError) as raised:
            opened(image)

        # Assert
        assert str(raised.value) == "disc.iso: no ISO 9660 volume descriptor at sector 16"


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
