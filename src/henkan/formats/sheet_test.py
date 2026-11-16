import pytest

from henkan.errors import FormatError
from henkan.formats import sheet
from henkan.source import memory_source


class TestReadingSheetText:
    def test_utf8_text_is_read_without_its_byte_order_mark(self):
        # Arrange
        source = memory_source(b'\xef\xbb\xbfFILE "J\xc3\xb3ia.bin" BINARY\n')

        # Act
        text = sheet.text(source)

        # Assert
        assert text == 'FILE "Jóia.bin" BINARY\n'

    def test_bytes_that_are_not_utf8_are_read_as_latin_one(self):
        # Arrange
        source = memory_source(b'FILE "J\xf3ia.bin" BINARY\n')

        # Act
        text = sheet.text(source)

        # Assert
        assert text == 'FILE "Jóia.bin" BINARY\n'

    def test_a_sheet_over_one_mebibyte_is_a_format_error(self):
        # Arrange
        source = memory_source(bytes(sheet.SHEET_MAX + 1), name="game.cue")

        # Act
        with pytest.raises(FormatError) as raised:
            sheet.text(source)

        # Assert
        assert str(raised.value) == "game.cue: a sheet of 1048577 bytes passes the limit of 1048576"


class TestTrackTypes:
    def test_only_the_types_chd_can_hold_are_known(self):
        # Arrange
        kinds = [*sheet.TrackType, None]

        # Act
        known = [kind for kind in kinds if sheet.known(kind)]

        # Assert
        assert known == [
            sheet.TrackType.AUDIO,
            sheet.TrackType.MODE1_2048,
            sheet.TrackType.MODE1_2352,
            sheet.TrackType.MODE2_2352,
        ]

    def test_every_type_has_its_stride(self):
        # Arrange
        kinds = list(sheet.TrackType)

        # Act
        strides = [sheet.STRIDES[kind] for kind in kinds]

        # Assert
        assert strides == [2352, 2048, 2352, 2352, 2336]
