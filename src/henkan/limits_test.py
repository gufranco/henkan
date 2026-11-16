import pytest

from henkan import limits
from henkan.errors import HenkanError


class TestTheReadLimit:
    def test_it_defaults_to_sixty_four_mebibytes(self):
        # Arrange
        environ: dict[str, str] = {}

        # Act
        limit = limits.read_max(environ)

        # Assert
        assert limit == 67_108_864

    def test_the_variable_overrides_it(self):
        # Arrange
        environ = {"HENKAN_READ_MAX": "4096"}

        # Act
        limit = limits.read_max(environ)

        # Assert
        assert limit == 4096

    def test_the_process_environment_is_read_when_none_is_given(self, monkeypatch):
        # Arrange
        monkeypatch.setenv("HENKAN_READ_MAX", "512")

        # Act
        limit = limits.read_max()

        # Assert
        assert limit == 512

    @pytest.mark.parametrize("value", ["", "0", "-1", "4k", "٤"])
    def test_a_value_that_is_not_a_positive_whole_number_is_refused(self, value):
        # Arrange
        environ = {"HENKAN_READ_MAX": value}

        # Act
        with pytest.raises(HenkanError) as raised:
            limits.read_max(environ)

        # Assert
        assert str(raised.value) == (
            f"HENKAN_READ_MAX must be a whole number of bytes above zero, not {value!r}"
        )
