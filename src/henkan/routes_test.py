from pathlib import Path

import pytest

from henkan import routes, targets
from henkan.errors import RefusalError
from henkan.formats.sheet import TrackType
from henkan.model import DiscClass, Format, Item, Platform, Trait
from henkan.routes import Step
from henkan.targets import Target

MODE1, MODE2, AUDIO = TrackType.MODE1_2352, TrackType.MODE2_2352, TrackType.AUDIO
COOKED = TrackType.MODE1_2048
EVERY_TRAIT = (frozenset(), *(frozenset({trait}) for trait in Trait))
SHAPES = ((), (COOKED,), (MODE1,), (MODE2,), (MODE2, AUDIO), (MODE1, AUDIO, MODE1))
CD_KINDS = (Format.CUE, Format.GDI, Format.TOC, Format.CCD, Format.MDS, Format.ISO, Format.BIN)
CONSOLE_KINDS = {
    Platform.GAMECUBE: (Format.ISO,),
    Platform.WII: (Format.ISO,),
    Platform.WII_U: (Format.WUD,),
    Platform.XBOX: (Format.ISO, Format.FOLDER),
    Platform.XBOX_360: (Format.ISO, Format.FOLDER),
    Platform.PS3: (Format.ISO, Format.FOLDER),
    Platform.SWITCH: (Format.FOLDER,),
    Platform.SWITCH_2: (Format.FOLDER,),
    Platform.N3DS: (Format.CCI, Format.CXI, Format.HOMEBREW_3DS),
}


def item(
    kind: Format,
    platform: Platform | None = None,
    tracks: tuple[TrackType | None, ...] = (),
    traits: frozenset[Trait] = frozenset(),
    discs: int = 1,
    size: int = 1000,
) -> Item:
    return Item(
        path=Path("game.pbp"),
        kind=kind,
        platform=platform,
        disc=DiscClass.CD,
        reason="",
        tracks=tracks,
        size=size,
        files=(Path("game.pbp"),),
        discs=discs,
        traits=traits,
    )


def every_item() -> list[Item]:
    cd = [
        item(kind, platform, shape)
        for kind in CD_KINDS
        for platform in (None, Platform.PS1, Platform.PS2, Platform.PSP, Platform.DREAMCAST)
        for shape in SHAPES
    ]
    cd.append(item(Format.CUE, Platform.DREAMCAST, (MODE1, AUDIO, MODE1, AUDIO)))
    console = [
        item(kind, platform, traits=traits)
        for platform, kinds in CONSOLE_KINDS.items()
        for kind in kinds
        for traits in EVERY_TRAIT
    ]
    packed = [item(Format.PBP, Platform.PS1, (MODE2, AUDIO), discs=discs) for discs in (1, 3)]
    return [*cd, *console, *packed]


class TestPlanningARoute:
    def test_a_direct_step_needs_no_temporary_space(self):
        # Arrange
        made = item(Format.CUE, Platform.PS1, (MODE2, AUDIO))

        # Act
        plan = routes.plan(made, "chd")

        # Assert
        assert plan == routes.Plan(
            made, Target(Format.CHD), (Step(Format.CUE, Format.CHD),), 0, 700
        )

    def test_a_pbp_reaches_cdi_through_a_cue_kept_in_temporary_space(self):
        # Arrange
        made = item(Format.PBP, Platform.PS1, (MODE2, AUDIO))

        # Act
        plan = routes.plan(made, "cdi")

        # Assert
        assert (plan.steps, plan.temporary, plan.output) == (
            (Step(Format.PBP, Format.CUE), Step(Format.CUE, Format.CDI)),
            1000,
            1000,
        )

    def test_a_plain_ps1_iso_reaches_pbp_through_a_chd_and_a_cue(self):
        # Arrange
        made = item(Format.ISO, Platform.PS1, (COOKED,))

        # Act
        plan = routes.plan(made, "pbp")

        # Assert
        assert (plan.steps, plan.temporary, plan.output) == (
            (
                Step(Format.ISO, Format.CHD),
                Step(Format.CHD, Format.CUE),
                Step(Format.CUE, Format.PBP),
            ),
            2000,
            800,
        )

    def test_one_disc_of_a_multi_disc_pbp_is_sized_as_its_share(self):
        # Arrange
        made = item(Format.PBP, Platform.PS1, (MODE2, AUDIO), discs=4)

        # Act
        plan = routes.plan(made, "chd_d2")

        # Assert
        assert (plan.target, plan.temporary, plan.output) == (Target(Format.CHD, 2), 250, 175)

    def test_a_gd_rom_set_is_rewritten_into_its_own_format_in_one_step(self):
        # Arrange
        made = item(Format.GDI, Platform.DREAMCAST, (MODE1, AUDIO, MODE1))

        # Act
        plan = routes.plan(made, "gdi")

        # Assert
        assert (plan.steps, plan.temporary) == ((Step(Format.GDI, Format.GDI),), 0)

    def test_without_a_named_target_the_first_offered_one_is_planned(self):
        # Arrange
        made = item(Format.FOLDER, Platform.SWITCH)

        # Act
        plan = routes.plan(made, None)

        # Assert
        assert (plan.target, plan.steps) == (
            Target(Format.NUP),
            (Step(Format.FOLDER, Format.NUP),),
        )

    @pytest.mark.parametrize(
        ("target", "output"),
        [("cso", 950), ("zso", 950), ("cso2", 950), ("chd", 700)],
    )
    def test_the_expected_output_follows_the_typical_ratio_of_its_format(self, target, output):
        # Arrange
        made = item(Format.ISO, Platform.PS2, (COOKED,))

        # Act
        plan = routes.plan(made, target)

        # Assert
        assert plan.output == output

    def test_artwork_takes_no_room(self):
        # Arrange
        made = item(Format.PBP, Platform.PS1, (MODE2, AUDIO))

        # Act
        plan = routes.plan(made, "art")

        # Assert
        assert plan.output == 0


class TestRefusingATarget:
    def test_a_target_the_item_is_not_offered_names_what_it_can_become(self):
        # Arrange
        made = item(Format.GDI, Platform.DREAMCAST, (MODE1, AUDIO, MODE1))

        # Act
        with pytest.raises(RefusalError) as raised:
            routes.plan(made, "rvz")

        # Assert
        assert str(raised.value) == (
            "game.pbp cannot become rvz; it can become: chd, gdi, cue, cdi, cue-ecc"
        )

    @pytest.mark.parametrize("target", ["rvz", "wia", "wbfs"])
    def test_a_wii_disc_asked_for_a_keyed_format_is_told_a_key_is_needed(self, target):
        # Arrange
        made = item(Format.ISO, Platform.WII)

        # Act
        with pytest.raises(RefusalError) as raised:
            routes.plan(made, target)

        # Assert
        assert str(raised.value) == (
            f"game.pbp cannot become {target}; it can become: gcz, ciso; {target} needs the Wii "
            "common key, which this version of henkan does not read"
        )


class TestTheGraph:
    def test_every_target_any_item_is_offered_has_a_route(self):
        # Arrange
        pairs = [(made, target) for made in every_item() for target in targets.offered(made)]

        # Act
        plans = [routes.plan(made, target.name) for made, target in pairs]

        # Assert
        assert len(pairs) > 300
        assert all(1 <= len(plan.steps) <= 3 for plan in plans)

    def test_a_pair_with_no_path_between_them_is_refused(self):
        # Arrange
        family = routes.GRAPH[routes.Family.SWITCH]

        # Act
        with pytest.raises(RefusalError) as raised:
            routes.route(family, Format.NUP, Format.CHD)

        # Assert
        assert str(raised.value) == "no chain of steps leads from nup to chd"
