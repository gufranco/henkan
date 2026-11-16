from henkan.formats.volume import Entry, find

ENTRIES = (Entry("SYSTEM.CNF", False, 20, 64), Entry("PSP_GAME", True, 21, 2048))


class TestFindingAnEntry:
    def test_names_match_whatever_their_case(self):
        # Arrange
        name = "system.cnf"

        # Act
        entry = find(ENTRIES, name)

        # Assert
        assert entry == ENTRIES[0]

    def test_a_missing_name_gives_none(self):
        # Arrange
        name = "UMD_DATA.BIN"

        # Act
        entry = find(ENTRIES, name)

        # Assert
        assert entry is None
