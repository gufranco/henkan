import struct

import pytest

from henkan.model import Platform
from henkan.platforms import xbox
from henkan.source import memory_source
from henkan.synthetic_test_support import patched, xdvdfs_volume


def package(magic: bytes, content: int) -> bytes:
    return patched(magic + bytes(0x400), 0x344, struct.pack(">I", content))


class TestIdentifyingAnXboxDisc:
    @pytest.mark.parametrize(
        ("names", "platform"),
        [
            (("Default.XEX", "media"), Platform.XBOX_360),
            (("DEFAULT.XBE", "media"), Platform.XBOX),
        ],
    )
    def test_the_boot_file_in_the_root_names_the_console(self, names, platform):
        # Arrange
        source = memory_source(xdvdfs_volume(names))

        # Act
        found = xbox.identify(source)

        # Assert
        assert found == (platform, 0)

    @pytest.mark.parametrize("image", [xdvdfs_volume(("readme.txt",)), bytes(0x11000)])
    def test_a_disc_without_a_boot_file_or_volume_is_not_xbox(self, image):
        # Arrange
        source = memory_source(image)

        # Act
        found = xbox.identify(source)

        # Assert
        assert found is None


class TestNamingADownloadPackage:
    @pytest.mark.parametrize(
        ("magic", "content", "kind"),
        [
            (b"LIVE", 0x7000, "Games on Demand"),
            (b"LIVE", 0xD0000, "Xbox Live Arcade"),
            (b"PIRS", 0xB0000, "title update"),
            (b"CON ", 0x2, "downloadable content"),
            (b"CON ", 0x4000, "installed game"),
            (b"LIVE", 0x1000, "downloaded Xbox 360 title"),
            (b"CON ", 0x1, "saved game"),
            (b"LIVE", 0x80000, "game demo"),
            (b"LIVE", 0x99, "download"),
        ],
    )
    def test_the_content_type_names_the_kind(self, magic, content, kind):
        # Arrange
        source = memory_source(package(magic, content))

        # Act
        found = xbox.package_kind(source)

        # Assert
        assert found == kind

    def test_a_package_cut_before_its_content_type_is_a_plain_download(self):
        # Arrange
        source = memory_source(b"LIVE" + bytes(16))

        # Act
        found = xbox.package_kind(source)

        # Assert
        assert found == "download"

    def test_a_file_that_is_no_package_has_no_kind(self):
        # Arrange
        source = memory_source(bytes(0x400))

        # Act
        found = xbox.package_kind(source)

        # Assert
        assert found is None


class TestIdentifyingAGameFolder:
    @pytest.mark.parametrize(
        ("name", "platform"),
        [("Default.xex", Platform.XBOX_360), ("DEFAULT.XBE", Platform.XBOX)],
    )
    def test_the_boot_file_at_its_top_names_the_console(self, tmp_path, name, platform):
        # Arrange
        (tmp_path / name).write_bytes(b"x")

        # Act
        found = xbox.folder(tmp_path)

        # Assert
        assert found == platform

    def test_a_folder_without_one_is_not_a_game(self, tmp_path):
        # Arrange
        (tmp_path / "default.xex").mkdir()

        # Act
        found = xbox.folder(tmp_path)

        # Assert
        assert found is None
