from pathlib import Path

import pytest

from henkan.formats.sheet import TrackType
from henkan.model import DiscClass, Format, Item, Platform, Trait, classify


def item(**changes: object) -> Item:
    values = {
        "path": Path("game.cue"),
        "kind": Format.CUE,
        "platform": Platform.PS1,
        "disc": DiscClass.CD,
        "reason": "a CUE sheet describes a CD",
        "tracks": (TrackType.MODE2_2352, TrackType.AUDIO),
        "size": 4704,
        "files": (Path("game.cue"), Path("game.bin")),
    }
    return Item(**{**values, **changes})


class TestAnItem:
    def test_optional_facts_start_empty(self):
        # Arrange
        made = item()

        # Act
        facts = (made.game_id, made.title, made.region, made.discs, made.warnings, made.traits)

        # Assert
        assert facts == ("", "", "", 1, (), frozenset())

    def test_track_types_are_known_when_chd_can_hold_every_one(self):
        # Arrange
        made = item()

        # Act
        known = made.types_known

        # Assert
        assert known is True

    def test_one_track_without_a_kind_makes_the_types_unknown(self):
        # Arrange
        made = item(tracks=(TrackType.MODE2_2352, None))

        # Act
        known = made.types_known

        # Assert
        assert known is False

    def test_an_item_without_tracks_has_no_known_types(self):
        # Arrange
        made = item(tracks=())

        # Act
        known = made.types_known

        # Assert
        assert known is False

    def test_a_trait_is_found_by_name(self):
        # Arrange
        made = item(traits=frozenset({Trait.FULL_DUMP}))

        # Act
        found = (made.has(Trait.FULL_DUMP), made.has(Trait.ENCRYPTED))

        # Assert
        assert found == (True, False)


class TestClassifyingADisc:
    @pytest.mark.parametrize(
        ("platform", "size", "expected"),
        [
            (Platform.PSP, 1, (DiscClass.DVD, "PSP games use DVD-class discs")),
            (
                Platform.PS2,
                737_280_000,
                (DiscClass.CD, "737,280,000 bytes fit a CD, which holds 737,280,000"),
            ),
            (
                None,
                737_280_001,
                (DiscClass.DVD, "737,280,001 bytes pass the CD limit of 737,280,000"),
            ),
        ],
    )
    def test_the_console_decides_first_and_the_size_second(self, platform, size, expected):
        # Arrange
        facts = (platform, size)

        # Act
        found = classify(*facts)

        # Assert
        assert found == expected
