import pytest

from henkan.model import Platform
from henkan.platforms import sega


class TestTheBootSector:
    @pytest.mark.parametrize(
        ("start", "platform"),
        [
            (b"SEGA SEGAKATANA SEGA ENTERPRISES", Platform.DREAMCAST),
            (b"SEGA SEGASATURN SEGA TP T-999   ", Platform.SATURN),
            (b"SEGADISCSYSTEM  SEGAIPSAMP      ", Platform.SEGA_CD),
            (b"SEGA MEGA DRIVE (C)T-999 1994   ", Platform.SEGA_CD),
            (b"SEGA SOMETHING ELSE             ", None),
            (b"", None),
        ],
    )
    def test_its_first_bytes_name_the_console(self, start, platform):
        # Arrange
        boot = start.ljust(2048, b"\0")

        # Act
        found = sega.identify(boot)

        # Assert
        assert found == platform
