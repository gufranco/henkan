from pathlib import Path

from henkan.cli import report
from henkan.commands import Offer
from henkan.formats.sheet import TrackType
from henkan.model import DiscClass, Format, Item, Platform, Trait
from henkan.routes import Plan, Step
from henkan.targets import Target

FULL = Item(
    path=Path("discs/game.cue"),
    kind=Format.CUE,
    platform=Platform.PS1,
    disc=DiscClass.CD,
    reason="a CUE sheet describes a CD",
    tracks=(TrackType.MODE2_2352, None),
    size=1_234_567,
    files=(Path("discs/game.cue"), Path("discs/game.bin")),
    game_id="ABCD-12345",
    title="Lantern Harbor",
    region="Europe",
    discs=2,
    warnings=("first warning",),
    traits=frozenset({Trait.RAW, Trait.NO_SHEET}),
)
BARE = Item(
    path=Path("data.iso"),
    kind=Format.ISO,
    platform=None,
    disc=DiscClass.CD,
    reason="40,960 bytes fit a CD, which holds 737,280,000",
    tracks=(),
    size=40_960,
    files=(Path("data.iso"),),
)
PLAN = Plan(
    FULL,
    Target(Format.CDI),
    (Step(Format.PBP, Format.CUE), Step(Format.CUE, Format.CDI)),
    1_234_567,
    1_234_567,
)


class TestInfoLines:
    def test_every_known_fact_gets_its_row(self):
        # Arrange
        item = FULL

        # Act
        lines = report.info_lines(item)

        # Assert
        assert lines == [
            "discs/game.cue",
            "  kind      cue",
            "  platform  PS1",
            "  disc      CD: a CUE sheet describes a CD",
            "  id        ABCD-12345",
            "  title     Lantern Harbor",
            "  region    Europe",
            "  discs     2",
            "  tracks    MODE2/2352, unknown",
            "  size      1,234,567 bytes",
            "  files     game.cue, game.bin",
            "  traits    no sheet, raw",
            "  warning   first warning",
        ]

    def test_an_item_with_few_facts_shows_only_those_and_an_unknown_platform(self):
        # Arrange
        item = BARE

        # Act
        lines = report.info_lines(item)

        # Assert
        assert lines == [
            "data.iso",
            "  kind      iso",
            "  platform  unknown",
            "  disc      CD: 40,960 bytes fit a CD, which holds 737,280,000",
            "  size      40,960 bytes",
            "  files     data.iso",
        ]


class TestItemJson:
    def test_it_carries_every_field_in_plain_values(self):
        # Arrange
        item = FULL

        # Act
        data = report.item_json(item)

        # Assert
        assert data == {
            "path": "discs/game.cue",
            "kind": "cue",
            "platform": "PS1",
            "disc": "CD",
            "reason": "a CUE sheet describes a CD",
            "id": "ABCD-12345",
            "title": "Lantern Harbor",
            "region": "Europe",
            "discs": 2,
            "tracks": ["MODE2/2352", None],
            "size": 1_234_567,
            "files": ["discs/game.cue", "discs/game.bin"],
            "traits": ["no sheet", "raw"],
            "warnings": ["first warning"],
        }

    def test_an_unknown_platform_is_null(self):
        # Arrange
        item = BARE

        # Act
        data = report.item_json(item)

        # Assert
        assert data["platform"] is None


class TestOfferLines:
    def test_the_first_target_is_marked_as_the_default(self):
        # Arrange
        offer = Offer(BARE, (Target(Format.CHD), Target(Format.CSO)))

        # Act
        lines = report.offer_lines(offer)

        # Assert
        assert lines == ["data.iso  unknown  CD  40,960 bytes", "  * chd", "    cso"]

    def test_json_names_the_default_and_every_target(self):
        # Arrange
        offer = Offer(FULL, (Target(Format.CHD), Target(Format.CUE, 2)))

        # Act
        data = report.offer_json(offer)

        # Assert
        assert data == {
            "path": "discs/game.cue",
            "platform": "PS1",
            "disc": "CD",
            "size": 1_234_567,
            "default": "chd",
            "targets": ["chd", "cue_d2"],
        }


class TestPlanLines:
    def test_each_step_is_named_with_the_temporary_space_it_leaves(self):
        # Arrange
        plan = PLAN

        # Act
        lines = report.plan_lines(plan)

        # Assert
        assert lines == [
            "discs/game.cue to cdi",
            "  1. pbp to cue, kept in a temporary folder: 1,234,567 bytes",
            "  2. cue to cdi",
            "  temporary space: 1,234,567 bytes",
            "  expected output: 1,234,567 bytes",
        ]

    def test_json_carries_the_steps_and_both_sizes(self):
        # Arrange
        plan = PLAN

        # Act
        data = report.plan_json(plan)

        # Assert
        assert data == {
            "path": "discs/game.cue",
            "target": "cdi",
            "steps": [
                {"from": "pbp", "to": "cue", "temporary": 1_234_567},
                {"from": "cue", "to": "cdi", "temporary": 0},
            ],
            "temporary": 1_234_567,
            "output": 1_234_567,
        }
