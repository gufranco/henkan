from pathlib import Path

import pytest

from henkan import images
from henkan.errors import RefusalError
from henkan.formats.sheet import TrackType
from henkan.model import CD_LIMIT, DiscClass, Format, Item, Platform, Trait
from henkan.source import open_source
from henkan.synthetic_test_support import (
    Tree,
    game_code,
    iso_image,
    nintendo_header,
    raw_image,
    rng,
    sfo,
    title,
    xdvdfs_volume,
)

LETTERS, DIGITS = game_code(rng())
NAME = title(rng())
CODE = f"{LETTERS}-{DIGITS}"
PS2: Tree = {"SYSTEM.CNF;1": f"BOOT2 = cdrom0:\\{LETTERS}_{DIGITS[:3]}.{DIGITS[3:]};1".encode()}
PS3: Tree = {"PS3_GAME": {"PARAM.SFO;1": sfo({"TITLE": NAME, "TITLE_ID": LETTERS + DIGITS})}}
NINTENDO = f"{LETTERS[:3]}E{DIGITS[:2]}"


def analyzed(path: Path) -> Item | None:
    with open_source(path) as source:
        return images.analyze(path, source)


def written(folder: Path, name: str, data: bytes, size: int | None = None) -> Path:
    path = folder / name
    with path.open("wb") as handle:
        handle.write(data)
        handle.truncate(len(data) if size is None else size)
    return path


class TestAPlainImage:
    def test_a_dvd_sized_iso_9660_volume_named_bin_is_a_ps2_dvd(self, tmp_path):
        # Arrange
        path = written(tmp_path, "game.bin", iso_image(PS2), CD_LIMIT + 2048)

        # Act
        item = analyzed(path)

        # Assert
        assert item == Item(
            path=path,
            kind=Format.ISO,
            platform=Platform.PS2,
            disc=DiscClass.DVD,
            reason="737,282,048 bytes pass the CD limit of 737,280,000",
            tracks=(TrackType.MODE1_2048,),
            size=CD_LIMIT + 2048,
            files=(path,),
            game_id=CODE,
        )

    def test_a_small_one_is_a_cd(self, tmp_path):
        # Arrange
        path = written(tmp_path, "game.iso", iso_image(PS2))

        # Act
        item = analyzed(path)

        # Assert
        assert (item.platform, item.disc) == (Platform.PS2, DiscClass.CD)

    def test_a_ps3_disc_is_dvd_class_and_carries_its_title(self, tmp_path):
        # Arrange
        path = written(tmp_path, "game.iso", iso_image(PS3))

        # Act
        item = analyzed(path)

        # Assert
        assert (item.platform, item.disc, item.reason, item.title) == (
            Platform.PS3,
            DiscClass.DVD,
            "PS3 games use DVD-class discs",
            NAME,
        )

    @pytest.mark.parametrize("name", ["data.iso", "data.img"])
    def test_whole_sectors_no_reader_recognizes_are_an_image_without_a_platform(
        self, tmp_path, name
    ):
        # Arrange
        path = written(tmp_path, name, bytes(2048 * 20))

        # Act
        item = analyzed(path)

        # Assert
        assert (item.kind, item.platform, item.tracks) == (
            Format.ISO,
            None,
            (TrackType.MODE1_2048,),
        )

    def test_a_volume_under_an_unrelated_name_is_still_an_image(self, tmp_path):
        # Arrange
        path = written(tmp_path, "backup.dat", iso_image({"README.TXT;1": b"hello"}))

        # Act
        item = analyzed(path)

        # Assert
        assert (item.kind, item.platform) == (Format.ISO, None)


class TestARawImage:
    @pytest.mark.parametrize(
        ("mode", "kind"), [(1, TrackType.MODE1_2352), (2, TrackType.MODE2_2352)]
    )
    def test_sync_bytes_make_it_a_cd_of_one_track_whatever_its_name(self, tmp_path, mode, kind):
        # Arrange
        path = written(tmp_path, "game.iso", raw_image(iso_image(PS2), mode))

        # Act
        item = analyzed(path)

        # Assert
        assert (item.kind, item.platform, item.disc, item.reason, item.tracks, item.traits) == (
            Format.BIN,
            Platform.PS2,
            DiscClass.CD,
            "raw CD sectors make a CD whatever the size",
            (kind,),
            frozenset({Trait.RAW}),
        )


class TestALoneBin:
    def test_without_sync_or_volume_it_is_taken_as_mode_two_with_a_warning(self, tmp_path):
        # Arrange
        path = written(tmp_path, "game.bin", bytes(2352 * 3))

        # Act
        item = analyzed(path)

        # Assert
        assert (item.kind, item.disc, item.tracks, item.traits, item.warnings) == (
            Format.BIN,
            DiscClass.CD,
            (TrackType.MODE2_2352,),
            frozenset({Trait.NO_SHEET}),
            ("no sheet describes this BIN, so its one track is taken as Mode 2 raw",),
        )

    @pytest.mark.parametrize("name", ["game.bin", "game.img"])
    def test_a_size_that_is_no_whole_number_of_sectors_is_refused(self, tmp_path, name):
        # Arrange
        path = written(tmp_path, name, bytes(5000))

        # Act
        with pytest.raises(RefusalError) as raised:
            analyzed(path)

        # Assert
        assert str(raised.value) == (
            f"{name} is cut short or not made of whole sectors: 5000 bytes is no multiple of "
            "2048 or 2352"
        )

    def test_an_img_of_raw_size_without_sync_is_refused(self, tmp_path):
        # Arrange
        path = written(tmp_path, "game.img", bytes(2352 * 3))

        # Act
        with pytest.raises(RefusalError) as raised:
            analyzed(path)

        # Assert
        assert str(raised.value) == (
            "game.img is cut short or not made of whole sectors: 7056 bytes is no multiple of "
            "2048 or 2352"
        )


class TestANintendoDisc:
    @pytest.mark.parametrize(
        ("wii", "platform"), [(True, Platform.WII), (False, Platform.GAMECUBE)]
    )
    def test_the_header_gives_console_id_title_and_region(self, tmp_path, wii, platform):
        # Arrange
        head = nintendo_header(NINTENDO, NAME, wii=wii)
        path = written(tmp_path, "game.iso", head, 2048 * 40)

        # Act
        item = analyzed(path)

        # Assert
        assert item == Item(
            path=path,
            kind=Format.ISO,
            platform=platform,
            disc=DiscClass.DVD,
            reason=f"{platform} games use DVD-class discs",
            tracks=(),
            size=2048 * 40,
            files=(path,),
            game_id=NINTENDO,
            title=NAME,
            region="USA",
        )

    def test_a_wii_u_disc_is_a_wud_whatever_its_name(self, tmp_path):
        # Arrange
        path = written(tmp_path, "game.iso", b"WUP-P-" + LETTERS.encode(), 0x8000 * 4)

        # Act
        item = analyzed(path)

        # Assert
        assert (item.kind, item.platform, item.game_id) == (Format.WUD, Platform.WII_U, LETTERS)

    @pytest.mark.parametrize("name", ["game.gcm", "game.wud"])
    def test_a_nintendo_name_on_something_else_is_refused(self, tmp_path, name):
        # Arrange
        path = written(tmp_path, name, bytes(2048 * 20))

        # Act
        with pytest.raises(RefusalError) as raised:
            analyzed(path)

        # Assert
        assert str(raised.value) == f"{name} is corrupt or not a disc image"


class TestAnXboxDisc:
    def test_a_trimmed_xbox_360_image_is_a_dvd_without_the_full_dump_trait(self, tmp_path):
        # Arrange
        path = written(tmp_path, "game.iso", xdvdfs_volume(("default.xex",)))

        # Act
        item = analyzed(path)

        # Assert
        assert (item.kind, item.platform, item.disc, item.traits) == (
            Format.ISO,
            Platform.XBOX_360,
            DiscClass.DVD,
            frozenset(),
        )

    def test_a_file_system_past_the_start_marks_a_full_dump(self, tmp_path):
        # Arrange
        path = tmp_path / "game.iso"
        with path.open("wb") as handle:
            handle.seek(0x18300000)
            handle.write(xdvdfs_volume(("default.xbe",)))

        # Act
        item = analyzed(path)

        # Assert
        assert (item.platform, item.traits) == (Platform.XBOX, frozenset({Trait.FULL_DUMP}))


class TestWhatIsNoImage:
    @pytest.mark.parametrize("name", ["tiny.iso", "tiny.bin", "tiny.img", "tiny.gcm", "tiny.wud"])
    @pytest.mark.parametrize("size", [1, 2048])
    def test_an_image_name_on_one_sector_or_less_is_too_small(self, tmp_path, name, size):
        # Arrange
        path = written(tmp_path, name, bytes(size))

        # Act
        with pytest.raises(RefusalError) as raised:
            analyzed(path)

        # Assert
        assert str(raised.value) == (
            f"{name} is too small to be a disc image: {size} bytes, when an image holds more "
            "than one sector of 2048 or 2352 bytes"
        )

    @pytest.mark.parametrize("size", [100, 2048 * 20])
    def test_unrecognized_content_under_an_unrelated_name_is_not_an_image(self, tmp_path, size):
        # Arrange
        path = written(tmp_path, "notes.dat", bytes(size))

        # Act
        item = analyzed(path)

        # Assert
        assert item is None
