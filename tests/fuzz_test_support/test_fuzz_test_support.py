from __future__ import annotations

from henkan import fuzz_test_support as fuzz
from henkan.errors import FormatError
from henkan.source import Source


def refuse(source: Source) -> None:
    raise FormatError(source.name)


def read_twice(source: Source) -> None:
    source.read(0, 2)
    source.read(1, 3)


class TestCorrupting:
    def test_each_mutation_lands_on_a_structure_byte_moved_by_its_shift(self):
        # Arrange
        base = bytes((0, 0, 7, 0, 0, 9, 0, 0))
        hot = fuzz.structure(base)

        # Act
        image = fuzz.corrupted(base, hot, [(0, 1, b"\xaa"), (3, -9, b"\xbb\xcc")], None)

        # Assert
        assert image == bytes((0xBB, 0xCC, 7, 0xAA, 0, 9, 0, 0))

    def test_a_cut_shortens_the_image(self):
        # Arrange
        base = bytes((1, 2, 3, 4))

        # Act
        image = fuzz.corrupted(base, fuzz.structure(base), [], 7)

        # Assert
        assert image == bytes((1, 2))


class TestAttempting:
    def test_a_format_error_is_a_refusal(self):
        # Arrange
        data = b"abcdef"

        # Act
        outcome = fuzz.attempt(refuse, data)

        # Assert
        assert outcome == fuzz.Outcome(refused=True, reads=0, largest=0)

    def test_a_clean_run_reports_how_much_it_read(self):
        # Arrange
        data = b"abcdef"

        # Act
        outcome = fuzz.attempt(read_twice, data)

        # Assert
        assert outcome == fuzz.Outcome(refused=False, reads=2, largest=3)

    def test_an_outcome_within_both_limits_is_bounded(self):
        # Arrange
        outcome = fuzz.Outcome(refused=False, reads=fuzz.READS_MAX, largest=fuzz.LIMIT)

        # Act
        bounded = outcome.bounded

        # Assert
        assert bounded is True

    def test_an_outcome_past_a_limit_is_not_bounded(self):
        # Arrange
        outcome = fuzz.Outcome(refused=False, reads=fuzz.READS_MAX + 1, largest=1)

        # Act
        bounded = outcome.bounded

        # Assert
        assert bounded is False
