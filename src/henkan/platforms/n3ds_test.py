import pytest

from henkan.errors import FormatError
from henkan.model import Format
from henkan.platforms import n3ds
from henkan.source import memory_source
from henkan.synthetic_test_support import ncch, ncsd


class TestIdentifyingA3dsFile:
    @pytest.mark.parametrize("decrypted", [True, False])
    def test_a_card_image_takes_its_state_from_its_first_partition(self, decrypted):
        # Arrange
        source = memory_source(ncsd(ncch(decrypted=decrypted)))

        # Act
        found = n3ds.identify(source)

        # Assert
        assert found == (Format.CCI, decrypted)

    @pytest.mark.parametrize("decrypted", [True, False])
    def test_an_executable_takes_its_state_from_its_own_header(self, decrypted):
        # Arrange
        source = memory_source(ncch(decrypted=decrypted))

        # Act
        found = n3ds.identify(source)

        # Assert
        assert found == (Format.CXI, decrypted)

    def test_homebrew_is_never_encrypted(self):
        # Arrange
        source = memory_source(b"3DSX" + bytes(64))

        # Act
        found = n3ds.identify(source)

        # Assert
        assert found == (Format.HOMEBREW_3DS, True)

    def test_anything_else_is_not_a_3ds_file(self):
        # Arrange
        source = memory_source(bytes(0x400))

        # Act
        found = n3ds.identify(source)

        # Assert
        assert found is None

    @pytest.mark.parametrize("partition", [bytes(0x200), b""])
    def test_a_card_image_whose_first_partition_is_no_executable_is_refused(self, partition):
        # Arrange
        source = memory_source(ncsd(partition), name="game.3ds")

        # Act
        with pytest.raises(FormatError) as raised:
            n3ds.identify(source)

        # Assert
        assert str(raised.value) == "game.3ds: a 3DS card image whose first partition is damaged"
