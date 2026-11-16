import io

import pytest

from henkan.errors import FormatError
from henkan.source import Source, memory_source, open_source


class TestReading:
    def test_it_returns_the_bytes_at_an_offset(self):
        # Arrange
        source = memory_source(b"0123456789")

        # Act
        data = source.read(3, 4)

        # Assert
        assert data == b"3456"

    @pytest.mark.parametrize(("offset", "length"), [(8, 3), (-1, 2), (0, -1), (11, 0)])
    def test_a_read_outside_the_file_is_a_format_error(self, offset, length):
        # Arrange
        source = memory_source(b"0123456789", name="disc.iso")

        # Act
        with pytest.raises(FormatError) as raised:
            source.read(offset, length)

        # Assert
        assert str(raised.value) == (
            f"disc.iso: {length} bytes at offset {offset} fall outside its 10 bytes"
        )

    def test_a_read_past_the_limit_is_a_format_error(self):
        # Arrange
        source = memory_source(bytes(64), name="disc.iso", limit=16)

        # Act
        with pytest.raises(FormatError) as raised:
            source.read(0, 17)

        # Assert
        assert str(raised.value) == "disc.iso: a read of 17 bytes passes the limit of 16"

    def test_a_file_that_ends_early_is_a_format_error(self):
        # Arrange
        source = Source(io.BytesIO(b"abc"), 10, 64, "disc.iso")

        # Act
        with pytest.raises(FormatError) as raised:
            source.read(0, 8)

        # Assert
        assert str(raised.value) == "disc.iso: the file ended before 8 bytes at 0"


class TestPeeking:
    @pytest.mark.parametrize(
        ("offset", "length", "expected"),
        [(0, 4, b"0123"), (8, 4, b"89"), (10, 4, b""), (20, 4, b""), (-1, 4, b"")],
    )
    def test_it_returns_what_exists_and_never_fails(self, offset, length, expected):
        # Arrange
        source = memory_source(b"0123456789")

        # Act
        data = source.peek(offset, length)

        # Assert
        assert data == expected


class TestOpeningAFile:
    def test_it_measures_the_file_and_names_the_source_after_it(self, tmp_path):
        # Arrange
        path = tmp_path / "disc.iso"
        path.write_bytes(b"0123456789")

        # Act
        with open_source(path, limit=8) as source:
            seen = (source.name, source.size, source.limit, source.read(2, 3))

        # Assert
        assert seen == ("disc.iso", 10, 8, b"234")

    def test_the_default_limit_comes_from_the_environment(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.setenv("HENKAN_READ_MAX", "2")
        path = tmp_path / "disc.iso"
        path.write_bytes(b"0123456789")

        # Act
        with open_source(path) as source:
            limit = source.limit

        # Assert
        assert limit == 2
