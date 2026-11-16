import pytest

from henkan import unread
from henkan.source import memory_source


class TestNamingAKindHenkanDoesNotReadYet:
    @pytest.mark.parametrize(
        ("head", "label"),
        [
            (b"WBFS", "a WBFS image"),
            (b"WUX0\x2e\xd0\x99\x10", "a WUX image"),
            (b"CISO", "a CSO or CISO image"),
            (b"ZISO", "a ZSO image"),
            (b"\x01\xc0\x0b\xb1", "a GCZ image"),
            (b"WIA\x01", "a WIA image"),
            (b"RVZ\x01", "an RVZ image"),
            (b"MComprHD", "a CHD"),
            (b"ECM\x00", "an ECM file"),
            (b"\x7fPKG", "a PS3 package"),
            (b"PFS0", "an NSP"),
            (b"NUP\x01", "a NUP"),
            (b"Z3DS", "a compressed 3DS file"),
            (bytes(0x100) + b"HEAD", "an XCI"),
        ],
    )
    def test_the_first_bytes_name_it_whatever_the_file_is_called(self, head, label):
        # Arrange
        source = memory_source(head + bytes(64))

        # Act
        found = unread.label(source, ".bin")

        # Assert
        assert found == label

    @pytest.mark.parametrize(
        ("extension", "label"),
        [
            (".nrg", "a Nero image"),
            (".cdi", "a DiscJuggler image"),
            (".vcd", "a POPStarter VCD"),
            (".zar", "a ZAR archive"),
            (".cia", "a CIA"),
            (".m3u", "a playlist"),
            (".zip", "an archive"),
            (".7z", "an archive"),
            (".dax", "a DAX image"),
        ],
    )
    def test_a_kind_with_no_leading_signature_is_named_by_its_extension(self, extension, label):
        # Arrange
        source = memory_source(bytes(64))

        # Act
        found = unread.label(source, extension)

        # Assert
        assert found == label

    def test_any_other_file_has_no_label(self):
        # Arrange
        source = memory_source(bytes(64))

        # Act
        found = unread.label(source, ".iso")

        # Assert
        assert found is None
