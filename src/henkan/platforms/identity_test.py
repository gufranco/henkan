from henkan.platforms.identity import UNKNOWN, Identity


class TestAnIdentity:
    def test_the_unknown_one_names_nothing(self):
        # Arrange
        unknown = UNKNOWN

        # Act
        facts = (unknown.platform, unknown.game_id, unknown.title, unknown.region)

        # Assert
        assert facts == (None, "", "", "")

    def test_two_identities_with_the_same_facts_are_equal(self):
        # Arrange
        first = Identity(None, "ABCD-12345")

        # Act
        second = Identity(None, "ABCD-12345")

        # Assert
        assert first == second
