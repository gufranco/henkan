from pathlib import Path

import pytest

from henkan import targets
from henkan.errors import UsageError
from henkan.formats.sheet import TrackType
from henkan.model import DiscClass, Format, Item, Platform, Trait
from henkan.targets import Target

MODE1, MODE2, AUDIO = TrackType.MODE1_2352, TrackType.MODE2_2352, TrackType.AUDIO
COOKED = TrackType.MODE1_2048


def item(
    kind: Format,
    platform: Platform | None = None,
    tracks: tuple[TrackType | None, ...] = (),
    traits: frozenset[Trait] = frozenset(),
    discs: int = 1,
) -> Item:
    return Item(
        path=Path("game"),
        kind=kind,
        platform=platform,
        disc=DiscClass.CD,
        reason="",
        tracks=tracks,
        size=1000,
        files=(Path("game"),),
        discs=discs,
        traits=traits,
    )


def names(found: tuple[Target, ...]) -> list[str]:
    return [target.name for target in found]


class TestCdItems:
    @pytest.mark.parametrize(
        ("made", "expected"),
        [
            (
                item(Format.CUE, Platform.PS1, (MODE2, AUDIO)),
                ["chd", "pbp", "vcd", "cdi", "cue-ecc"],
            ),
            (
                item(Format.CUE, Platform.PS1, (MODE2,)),
                ["chd", "iso", "cso", "zso", "cso2", "pbp", "vcd", "cdi", "cue-ecc", "ecm"],
            ),
            (
                item(Format.CUE, Platform.PS1, (MODE1,)),
                ["chd", "iso", "cso", "zso", "cso2", "pbp", "cdi", "cue-ecc", "ecm"],
            ),
            (item(Format.CUE, Platform.SATURN, (MODE1, AUDIO)), ["chd", "cdi", "cue-ecc"]),
            (item(Format.CUE, None, (COOKED, AUDIO)), ["chd"]),
            (item(Format.CUE, None, (MODE2, None)), ["chd"]),
            (
                item(Format.GDI, Platform.DREAMCAST, (MODE1, AUDIO, MODE1)),
                ["chd", "gdi", "cue", "cdi", "cue-ecc"],
            ),
            (
                item(Format.CUE, Platform.DREAMCAST, (MODE1, AUDIO, MODE1, AUDIO)),
                ["chd", "gdi", "cue", "cdi", "cue-ecc"],
            ),
            (
                item(Format.CUE, Platform.DREAMCAST, (AUDIO, AUDIO, MODE2)),
                ["chd", "cdi", "cue-ecc"],
            ),
            (item(Format.CUE, Platform.DREAMCAST, (MODE1, AUDIO)), ["chd", "cdi", "cue-ecc"]),
            (item(Format.TOC, Platform.PS1, ()), ["chd"]),
            (
                item(Format.CCD, Platform.PS1, (MODE2, AUDIO)),
                ["chd", "cue", "pbp", "vcd", "cdi", "cue-ecc"],
            ),
            (item(Format.MDS, None, (COOKED,)), ["chd", "cue", "iso", "cso", "zso", "cso2"]),
            (item(Format.ISO, Platform.PS2, (COOKED,)), ["chd", "cso", "zso", "cso2"]),
            (item(Format.ISO, Platform.PS1, (COOKED,)), ["chd", "cso", "zso", "cso2", "pbp"]),
            (
                item(Format.BIN, None, (MODE2,), frozenset({Trait.RAW})),
                ["chd", "iso", "cso", "zso", "cso2", "cdi", "cue-ecc", "ecm"],
            ),
            (
                item(Format.PBP, Platform.PS1, (MODE2, AUDIO)),
                ["chd", "cue", "art", "vcd", "cdi", "cue-ecc"],
            ),
        ],
    )
    def test_each_is_offered_what_its_tracks_and_console_allow(self, made, expected):
        # Arrange
        subject = made

        # Act
        found = targets.offered(subject)

        # Assert
        assert names(found) == expected

    def test_a_multi_disc_pbp_also_offers_each_disc_alone(self):
        # Arrange
        made = item(Format.PBP, Platform.PS1, (MODE2, AUDIO), discs=2)

        # Act
        found = targets.offered(made)

        # Assert
        assert names(found) == ["chd", "cue", "art", "chd_d1", "cue_d1", "chd_d2", "cue_d2"]


class TestConsoleItems:
    @pytest.mark.parametrize(
        ("made", "expected"),
        [
            (item(Format.ISO, Platform.GAMECUBE), ["rvz", "gcz", "wia", "ciso"]),
            (item(Format.ISO, Platform.WII), ["gcz", "ciso"]),
            (item(Format.WUD, Platform.WII_U), ["wux"]),
            (item(Format.FOLDER, Platform.SWITCH), ["nup"]),
            (item(Format.FOLDER, Platform.SWITCH_2), ["nup"]),
            (item(Format.CCI, Platform.N3DS), ["zcci", "cia"]),
            (item(Format.CCI, Platform.N3DS, traits=frozenset({Trait.ENCRYPTED})), ["zcci"]),
            (item(Format.CXI, Platform.N3DS), ["zcxi"]),
            (item(Format.HOMEBREW_3DS, Platform.N3DS), ["z3dsx"]),
            (item(Format.ISO, Platform.PS3, (COOKED,)), ["chd"]),
            (item(Format.FOLDER, Platform.PS3), ["iso", "chd"]),
            (item(Format.FOLDER, Platform.PS3, traits=frozenset({Trait.PSN})), ["pkg"]),
            (item(Format.ISO, Platform.XBOX), ["chd", "folder"]),
            (
                item(Format.ISO, Platform.XBOX, traits=frozenset({Trait.FULL_DUMP})),
                ["chd", "xiso", "folder"],
            ),
            (
                item(Format.ISO, Platform.XBOX_360, traits=frozenset({Trait.FULL_DUMP})),
                ["chd", "zar", "folder"],
            ),
            (item(Format.FOLDER, Platform.XBOX), ["chd", "iso"]),
            (item(Format.FOLDER, Platform.XBOX_360), ["chd", "iso", "zar"]),
        ],
    )
    def test_each_is_offered_its_console_formats_minus_its_own(self, made, expected):
        # Arrange
        subject = made

        # Act
        found = targets.offered(subject)

        # Assert
        assert names(found) == expected

    def test_a_wii_disc_gains_the_keyed_formats_once_a_key_is_present(self):
        # Arrange
        made = item(Format.ISO, Platform.WII)

        # Act
        found = targets.offered(made, wii_key=True)

        # Assert
        assert names(found) == ["rvz", "gcz", "wia", "ciso", "wbfs"]


class TestNamingATarget:
    @pytest.mark.parametrize(
        ("name", "target"),
        [
            ("chd", Target(Format.CHD)),
            ("CSO2", Target(Format.CSO2)),
            ("cue_d3", Target(Format.CUE, 3)),
        ],
    )
    def test_a_name_parses_to_its_format_and_disc(self, name, target):
        # Arrange
        text = name

        # Act
        found = targets.parse(text)

        # Assert
        assert (found, found.name) == (target, name.lower())

    @pytest.mark.parametrize("name", ["mp3", "chd_d0", "chd_dx", ""])
    def test_an_unknown_name_is_a_usage_error_listing_the_valid_ones(self, name):
        # Arrange
        text = name

        # Act
        with pytest.raises(UsageError) as raised:
            targets.parse(text)

        # Assert
        assert str(raised.value) == (
            f"{name!r} is not a target; the targets are: " + ", ".join(sorted(Format))
        )
