import pytest

from henkan import tree
from henkan.errors import RefusalError


class TestFindingAChild:
    def test_the_name_matches_whatever_its_case(self, tmp_path):
        # Arrange
        (tmp_path / "Default.XBE").write_bytes(b"x")

        # Act
        found = tree.child(tmp_path, "default.xbe")

        # Assert
        assert found == tmp_path / "Default.XBE"

    def test_a_missing_name_gives_none(self, tmp_path):
        # Arrange
        (tmp_path / "other.bin").write_bytes(b"x")

        # Act
        found = tree.child(tmp_path, "default.xbe")

        # Assert
        assert found is None

    def test_a_path_that_is_no_folder_has_no_children(self, tmp_path):
        # Arrange
        path = tmp_path / "absent"

        # Act
        found = tree.child(path, "default.xbe")

        # Assert
        assert found is None

    def test_none_has_no_children(self):
        # Arrange
        folder = None

        # Act
        found = tree.child(folder, "default.xbe")

        # Assert
        assert found is None


class TestMeasuringAFolder:
    def test_it_counts_files_and_bytes_at_every_depth_and_skips_links(self, tmp_path):
        # Arrange
        (tmp_path / "a.bin").write_bytes(bytes(10))
        (tmp_path / "deep" / "er").mkdir(parents=True)
        (tmp_path / "deep" / "er" / "b.bin").write_bytes(bytes(32))
        (tmp_path / "link").symlink_to(tmp_path / "a.bin")

        # Act
        measured = tree.measure(tmp_path)

        # Assert
        assert measured == (2, 42)

    def test_a_folder_with_too_many_files_is_refused(self, tmp_path):
        # Arrange
        for index in range(3):
            (tmp_path / f"{index}.bin").write_bytes(b"x")

        # Act
        with pytest.raises(RefusalError) as raised:
            tree.measure(tmp_path, limit=2)

        # Assert
        assert str(raised.value) == f"{tmp_path.name} holds more than 2 files"
