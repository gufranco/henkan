import pytest

from henkan.errors import FormatError
from henkan.formats import sectors
from henkan.source import memory_source
from henkan.synthetic_test_support import raw_image


def numbered(count: int) -> bytes:
    return b"".join(bytes((index,)) * sectors.SECTOR for index in range(count))


class TestASectorView:
    @pytest.mark.parametrize(
        ("layout", "image"),
        [
            (sectors.COOKED, numbered(4)),
            (sectors.RAW_MODE1, raw_image(numbered(4), 1)),
            (sectors.RAW_MODE2, raw_image(numbered(4), 2)),
        ],
    )
    def test_it_returns_the_user_bytes_of_a_sector(self, layout, image):
        # Arrange
        view = sectors.SectorView(memory_source(image), layout)

        # Act
        data = view.sector(2)

        # Assert
        assert data == bytes((2,)) * 2048

    def test_the_base_moves_sector_zero(self):
        # Arrange
        view = sectors.SectorView(memory_source(b"junk" + numbered(3)), sectors.COOKED, 4)

        # Act
        data = view.sector(1)

        # Assert
        assert data == bytes((1,)) * 2048

    def test_a_negative_sector_is_a_format_error(self):
        # Arrange
        view = sectors.SectorView(memory_source(numbered(2), name="disc.iso"), sectors.COOKED)

        # Act
        with pytest.raises(FormatError) as raised:
            view.sector(-1)

        # Assert
        assert str(raised.value) == "disc.iso: sector -1 does not exist"

    def test_a_read_spans_sectors_and_stops_at_the_length(self):
        # Arrange
        view = sectors.SectorView(memory_source(raw_image(numbered(4), 2)), sectors.RAW_MODE2)

        # Act
        data = view.read(1, 2050)

        # Assert
        assert data == bytes((1,)) * 2048 + bytes((2,)) * 2

    @pytest.mark.parametrize("length", [-1, 4097])
    def test_a_read_past_the_limit_is_a_format_error(self, length):
        # Arrange
        source = memory_source(numbered(4), name="disc.iso", limit=4096)
        view = sectors.SectorView(source, sectors.COOKED)

        # Act
        with pytest.raises(FormatError) as raised:
            view.read(0, length)

        # Assert
        assert str(raised.value) == (f"disc.iso: a read of {length} bytes passes the limit of 4096")


class TestTheRawMode:
    @pytest.mark.parametrize("mode", [1, 2])
    def test_sync_bytes_and_a_mode_give_the_mode(self, mode):
        # Arrange
        source = memory_source(raw_image(numbered(1), mode))

        # Act
        found = sectors.raw_mode(source)

        # Assert
        assert found == mode

    @pytest.mark.parametrize(
        "image",
        [
            numbered(1),
            sectors.SYNC + bytes(3),
            sectors.SYNC + bytes((0, 2, 0, 3)),
            b"",
        ],
    )
    def test_anything_else_gives_none(self, image):
        # Arrange
        source = memory_source(image)

        # Act
        found = sectors.raw_mode(source)

        # Assert
        assert found is None
