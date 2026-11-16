import struct

import pytest
from hypothesis import given

from henkan.errors import FormatError
from henkan.formats import sectors, udf
from henkan.formats.volume import find
from henkan.fuzz_test_support import CUTS, FUZZ, MUTATIONS, attempt, corrupted, structure
from henkan.source import Source, memory_source
from henkan.synthetic_test_support import (
    UdfOptions,
    patched,
    udf_identifier,
    udf_image,
    udf_tag,
)

CNF = b"BOOT2 = cdrom0:\\SLUS_123.45;1\r\n"
LEVEL = bytes(range(250)) * 20
TREE = {"SYSTEM.CNF": CNF, "DATA": {"LEVEL.BIN": LEVEL}}
SMALL = {"SYSTEM.CNF": CNF, "DATA": {"LEVEL.BIN": LEVEL[:300]}}
IMAGE = udf_image(TREE, label="HENKAN")
HOT = structure(IMAGE)
SECTOR = sectors.SECTOR
PARTITION = 32 * SECTOR
LOGICAL = 33 * SECTOR
ANCHOR = 256 * SECTOR
FILE_SET = 272 * SECTOR
ROOT_ENTRY = 273 * SECTOR
CNF_ENTRY = 274 * SECTOR
CNF_RECORD = IMAGE.index(udf_identifier("SYSTEM.CNF", 2))
TERMINATOR = udf_tag(8, b"")


def opened(image: bytes) -> udf.UdfVolume:
    view = sectors.SectorView(memory_source(image, name="disc.iso"), sectors.COOKED)
    return udf.read_volume(view)


def explore(source: Source) -> None:
    volume = udf.read_volume(sectors.SectorView(source, sectors.COOKED))
    for entry in volume.root():
        if entry.directory:
            volume.children(entry)
        else:
            volume.read(entry, 64)


class TestReadingAVolume:
    def test_the_root_lists_each_entry_with_its_kind_and_size(self):
        # Arrange
        volume = opened(IMAGE)

        # Act
        entries = volume.root()

        # Assert
        assert [(entry.name, entry.directory, entry.size) for entry in entries] == [
            ("SYSTEM.CNF", False, 31),
            ("DATA", True, 88),
        ]

    def test_the_label_comes_from_the_logical_volume(self):
        # Arrange
        image = IMAGE

        # Act
        volume = opened(image)

        # Assert
        assert volume.label == "HENKAN"

    def test_a_volume_without_a_label_has_an_empty_one(self):
        # Arrange
        image = udf_image(SMALL)

        # Act
        volume = opened(image)

        # Assert
        assert volume.label == ""

    def test_a_file_spanning_sectors_reads_whole(self):
        # Arrange
        volume = opened(IMAGE)
        entry = volume.children(volume.root()[1])[0]

        # Act
        data = volume.read(entry, 1_000_000)

        # Assert
        assert data == LEVEL

    @pytest.mark.parametrize("extended", [False, True])
    @pytest.mark.parametrize("allocation", [0, 1, 3])
    def test_every_entry_form_and_allocation_kind_reads_the_same(self, extended, allocation):
        # Arrange
        options = UdfOptions(extended=extended, allocation=allocation)
        volume = opened(udf_image(SMALL, options=options))
        entry = volume.children(volume.root()[1])[0]

        # Act
        data = volume.read(entry, 200)

        # Assert
        assert data == LEVEL[:200]

    def test_a_name_outside_latin_one_is_read_as_sixteen_bit_text(self):
        # Arrange
        volume = opened(udf_image({"ゲーム.BIN": b"data"}))

        # Act
        entries = volume.root()

        # Assert
        assert [entry.name for entry in entries] == ["ゲーム.BIN"]

    def test_a_deleted_entry_is_left_out(self):
        # Arrange
        volume = opened(patched(IMAGE, CNF_RECORD + 18, b"\x04"))

        # Act
        entries = volume.root()

        # Assert
        assert [entry.name for entry in entries] == ["DATA"]


class TestRefusingWhatIsNotAUdfVolume:
    @pytest.mark.parametrize(
        "image",
        [
            patched(IMAGE, 17 * SECTOR, b"\0XXX00"),
            patched(IMAGE, 16 * SECTOR, (b"\0BEA01" + bytes(SECTOR - 6)) * 16),
        ],
    )
    def test_a_disc_without_the_recognition_sequence(self, image):
        # Arrange
        damaged = image

        # Act
        with pytest.raises(FormatError) as raised:
            opened(damaged)

        # Assert
        assert str(raised.value) == "disc.iso: no UDF volume recognition sequence"

    def test_a_structure_that_fails_its_checksum(self):
        # Arrange
        image = patched(IMAGE, ANCHOR + 6, b"\x01")

        # Act
        with pytest.raises(FormatError) as raised:
            opened(image)

        # Assert
        assert str(raised.value) == "a volume structure fails its checksum"

    def test_an_anchor_sector_holding_another_structure(self):
        # Arrange
        image = patched(IMAGE, ANCHOR, TERMINATOR)

        # Act
        with pytest.raises(FormatError) as raised:
            opened(image)

        # Assert
        assert str(raised.value) == "sector 256 holds descriptor 8, not 2"

    @pytest.mark.parametrize(
        "image",
        [
            patched(IMAGE, PARTITION, TERMINATOR),
            patched(IMAGE, ANCHOR, udf_tag(2, struct.pack("<II", 0, 32))),
        ],
    )
    def test_a_descriptor_sequence_without_a_partition(self, image):
        # Arrange
        damaged = image

        # Act
        with pytest.raises(FormatError) as raised:
            opened(damaged)

        # Assert
        assert str(raised.value) == "disc.iso: the UDF volume names no partition"

    @pytest.mark.parametrize(
        ("offset", "damage"),
        [
            (LOGICAL + 212, struct.pack("<I", 512)),
            (LOGICAL + 256, b"\x01"),
            (LOGICAL + 268, bytes(4)),
            (LOGICAL + 440, b"\x02"),
        ],
    )
    def test_a_partition_layout_henkan_does_not_read(self, offset, damage):
        # Arrange
        image = patched(IMAGE, offset, damage)

        # Act
        with pytest.raises(FormatError) as raised:
            opened(image)

        # Assert
        assert str(raised.value) == "the UDF volume uses a partition layout henkan does not read"

    def test_a_partition_map_naming_a_missing_partition(self):
        # Arrange
        image = patched(IMAGE, PARTITION + 22, b"\x07")

        # Act
        with pytest.raises(FormatError) as raised:
            opened(image)

        # Assert
        assert str(raised.value) == "the UDF volume's partition map names a missing partition"

    def test_a_root_directory_in_another_partition(self):
        # Arrange
        image = patched(IMAGE, FILE_SET + 408, b"\x01")

        # Act
        with pytest.raises(FormatError) as raised:
            opened(image)

        # Assert
        assert str(raised.value) == (
            "the UDF root directory sits in a partition henkan does not read"
        )


class TestRefusingADamagedDirectory:
    @pytest.mark.parametrize(
        ("offset", "damage", "reason"),
        [
            (ROOT_ENTRY, TERMINATOR, "block 1 holds descriptor 8, not a file entry"),
            (
                ROOT_ENTRY + 172,
                struct.pack("<I", 5000),
                "the file entry at block 1 runs past its sector",
            ),
            (
                ROOT_ENTRY + 56,
                struct.pack("<Q", 2 * 1024 * 1024),
                "a directory of 2097152 bytes passes the limit of 1048576",
            ),
            (
                CNF_RECORD,
                udf_tag(8, b"", size=16),
                "a directory record at byte 40 is damaged",
            ),
            (CNF_RECORD + 28, b"\x01", "a directory record at byte 40 is damaged"),
            (CNF_RECORD + 19, b"\xf0", "a directory record at byte 40 is damaged"),
            (
                CNF_RECORD + 38,
                b"\x09",
                "a file name uses a character encoding henkan does not read",
            ),
        ],
    )
    def test_the_root_is_refused_with_its_reason(self, offset, damage, reason):
        # Arrange
        volume = opened(patched(IMAGE, offset, damage))

        # Act
        with pytest.raises(FormatError) as raised:
            volume.root()

        # Assert
        assert str(raised.value) == reason

    def test_a_file_has_no_children(self):
        # Arrange
        volume = opened(IMAGE)
        entry = find(volume.root(), "SYSTEM.CNF")

        # Act
        with pytest.raises(FormatError) as raised:
            volume.children(entry)

        # Assert
        assert str(raised.value) == "'SYSTEM.CNF' is a file, not a directory"

    def test_a_directory_with_too_many_entries(self):
        # Arrange
        crowd = {f"F{index}": b"" for index in range(udf.CHILDREN_MAX + 1)}
        volume = opened(udf_image(crowd))

        # Act
        with pytest.raises(FormatError) as raised:
            volume.root()

        # Assert
        assert str(raised.value) == "a directory holds more than 4096 entries"


class TestRefusingADamagedFile:
    def test_an_allocation_kind_henkan_does_not_read(self):
        # Arrange
        volume = opened(udf_image(SMALL, options=UdfOptions(allocation=2)))

        # Act
        with pytest.raises(FormatError) as raised:
            volume.root()

        # Assert
        assert str(raised.value) == "allocation type 2 is not one henkan reads"

    def test_an_extent_that_was_never_recorded(self):
        # Arrange
        volume = opened(patched(IMAGE, CNF_ENTRY + 176, struct.pack("<I", 0x4000001F)))
        entry = find(volume.root(), "SYSTEM.CNF")

        # Act
        with pytest.raises(FormatError) as raised:
            volume.read(entry, 31)

        # Assert
        assert str(raised.value) == "a file extent is not recorded on the disc"

    def test_an_extent_in_another_partition(self):
        # Arrange
        image = udf_image(SMALL, options=UdfOptions(allocation=1))
        volume = opened(patched(image, CNF_ENTRY + 176 + 8, b"\x01"))
        entry = find(volume.root(), "SYSTEM.CNF")

        # Act
        with pytest.raises(FormatError) as raised:
            volume.read(entry, 31)

        # Assert
        assert str(raised.value) == "a file extent sits in a partition henkan does not read"

    def test_extents_that_end_before_the_recorded_length(self):
        # Arrange
        volume = opened(patched(IMAGE, CNF_ENTRY + 56, struct.pack("<Q", 5000)))
        entry = find(volume.root(), "SYSTEM.CNF")

        # Act
        with pytest.raises(FormatError) as raised:
            volume.read(entry, 5000)

        # Assert
        assert str(raised.value) == "a file's extents end before its recorded length"


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
