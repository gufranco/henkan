from pathlib import Path

import pytest
from hypothesis import given

from henkan import detect
from henkan.errors import HenkanError, OrphanError, RefusalError, UnsupportedError
from henkan.formats.sheet import TrackType
from henkan.fuzz_test_support import CUTS, MUTATIONS, QUICK, attempt, corrupted, structure
from henkan.model import DiscClass, Format, Item, Platform, Trait
from henkan.synthetic_test_support import (
    MdsTrack,
    game_code,
    iso_image,
    mds_image,
    ncch,
    ncsd,
    nintendo_header,
    patched,
    pbp_image,
    raw_image,
    rng,
    udf_image,
    xdvdfs_volume,
)

LETTERS, DIGITS = game_code(rng())
CODE = f"{LETTERS}-{DIGITS}"
PS1 = raw_image(
    iso_image({"SYSTEM.CNF;1": f"BOOT = cdrom:\\{LETTERS}_{DIGITS[:3]}.{DIGITS[3:]};1".encode()}),
    2,
)


def written(folder: Path, name: str, data: bytes) -> Path:
    path = folder / name
    path.write_bytes(data)
    return path


class TestInspectingAFile:
    def test_a_sheet_is_read_with_the_files_it_names(self, tmp_path):
        # Arrange
        written(tmp_path, "game.bin", PS1)
        path = written(tmp_path, "game.cue", b'FILE "game.bin" BINARY\nTRACK 01 MODE2/2352\n')

        # Act
        item = detect.inspect(path)

        # Assert
        assert (item.kind, item.platform, item.game_id) == (Format.CUE, Platform.PS1, CODE)

    def test_an_image_is_read_by_its_content(self, tmp_path):
        # Arrange
        path = written(tmp_path, "game.dat", PS1)

        # Act
        item = detect.inspect(path)

        # Assert
        assert (item.kind, item.platform, item.game_id) == (Format.BIN, Platform.PS1, CODE)

    def test_a_folder_is_read_as_a_game_folder(self, tmp_path):
        # Arrange
        written(tmp_path, "default.xbe", b"x")

        # Act
        item = detect.inspect(tmp_path)

        # Assert
        assert (item.kind, item.platform) == (Format.FOLDER, Platform.XBOX)


class TestAPbp:
    @pytest.mark.parametrize("discs", [1, 3])
    def test_it_is_a_ps1_cd_set_with_its_disc_count_and_dashed_id(self, tmp_path, discs):
        # Arrange
        image = pbp_image(discs, {"DISC_ID": LETTERS + DIGITS})
        path = written(tmp_path, "game.pbp", image)

        # Act
        item = detect.inspect(path)

        # Assert
        assert item == Item(
            path=path,
            kind=Format.PBP,
            platform=Platform.PS1,
            disc=DiscClass.CD,
            reason="a PBP holds PS1 CDs",
            tracks=(TrackType.MODE2_2352, TrackType.AUDIO),
            size=len(image) * 8 // 5,
            files=(path,),
            game_id=CODE,
            discs=discs,
        )

    def test_an_id_of_another_shape_is_kept_as_written(self, tmp_path):
        # Arrange
        path = written(tmp_path, "game.pbp", pbp_image(1, {"DISC_ID": "HOMEBREW1"}))

        # Act
        item = detect.inspect(path)

        # Assert
        assert item.game_id == "HOMEBREW1"


class TestA3dsFile:
    def test_a_decrypted_card_image_is_a_dvd_class_3ds_item(self, tmp_path):
        # Arrange
        path = written(tmp_path, "game.3ds", ncsd(ncch(decrypted=True)))

        # Act
        item = detect.inspect(path)

        # Assert
        assert (item.kind, item.platform, item.disc, item.traits, item.warnings) == (
            Format.CCI,
            Platform.N3DS,
            DiscClass.DVD,
            frozenset(),
            (),
        )

    def test_an_encrypted_dump_carries_the_trait_and_a_warning(self, tmp_path):
        # Arrange
        path = written(tmp_path, "game.cxi", ncch(decrypted=False))

        # Act
        item = detect.inspect(path)

        # Assert
        assert (item.kind, item.traits, item.warnings) == (
            Format.CXI,
            frozenset({Trait.ENCRYPTED}),
            ("an encrypted dump can be compressed, but emulators run only decrypted dumps",),
        )


class TestStandIns:
    def test_an_mdf_with_its_mds_beside_it_stands_for_the_mds(self, tmp_path):
        # Arrange
        data = written(tmp_path, "game.mdf", PS1)
        sheet = written(tmp_path, "game.mds", mds_image((MdsTrack(0xAB, 1, 2352, 0, 0),), "*.mdf"))

        # Act
        item = detect.inspect(data)

        # Assert
        assert (item.path, item.kind, item.platform) == (sheet, Format.MDS, Platform.PS1)

    def test_an_mdf_alone_is_refused_as_track_data_without_its_descriptor(self, tmp_path):
        # Arrange
        path = written(tmp_path, "game.mdf", PS1)

        # Act
        with pytest.raises(OrphanError) as raised:
            detect.inspect(path)

        # Assert
        assert str(raised.value) == (
            "game.mdf holds track data only and cannot be read without its MDS descriptor"
        )

    def test_a_sub_with_its_ccd_beside_it_stands_for_the_ccd(self, tmp_path):
        # Arrange
        written(tmp_path, "game.img", PS1)
        side = written(tmp_path, "game.sub", b"sub")
        sheet = written(
            tmp_path, "game.ccd", b"[CloneCD]\n[Disc]\nSessions=1\n[TRACK 1]\nMODE=2\nINDEX 1=0\n"
        )

        # Act
        item = detect.inspect(side)

        # Assert
        assert (item.path, item.kind) == (sheet, Format.CCD)


class TestRefusals:
    def test_a_path_that_does_not_exist(self, tmp_path):
        # Arrange
        path = tmp_path / "absent.iso"

        # Act
        with pytest.raises(RefusalError) as raised:
            detect.inspect(path)

        # Assert
        assert str(raised.value) == "absent.iso: no such file or folder"

    def test_an_empty_file(self, tmp_path):
        # Arrange
        path = written(tmp_path, "game.iso", b"")

        # Act
        with pytest.raises(RefusalError) as raised:
            detect.inspect(path)

        # Assert
        assert str(raised.value) == "game.iso is empty"

    def test_an_xbox_360_download_package_is_named_and_explained(self, tmp_path):
        # Arrange
        package = patched(b"LIVE" + bytes(0x400), 0x344, (0xD0000).to_bytes(4, "big"))
        path = written(tmp_path, "game.iso", package)

        # Act
        with pytest.raises(RefusalError) as raised:
            detect.inspect(path)

        # Assert
        assert str(raised.value) == (
            "game.iso is an Xbox 360 Xbox Live Arcade package, not a disc; it needs no "
            "conversion, since emulators load such packages directly"
        )

    def test_a_kind_this_version_does_not_read_is_named(self, tmp_path):
        # Arrange
        path = written(tmp_path, "game.iso", b"RVZ\x01" + bytes(64))

        # Act
        with pytest.raises(RefusalError) as raised:
            detect.inspect(path)

        # Assert
        assert str(raised.value) == (
            "game.iso is an RVZ image, which this version of henkan does not read"
        )
        assert not isinstance(raised.value, UnsupportedError)

    @pytest.mark.parametrize("name", ["notes.txt", "stray.sub"])
    def test_any_other_file_is_not_a_kind_henkan_converts(self, tmp_path, name):
        # Arrange
        path = written(tmp_path, name, b"just some words\n")

        # Act
        with pytest.raises(UnsupportedError) as raised:
            detect.inspect(path)

        # Assert
        assert str(raised.value) == f"{name} is not a kind of file henkan converts"


BASES = {
    "iso": iso_image({"SYSTEM.CNF;1": b"BOOT2 = cdrom0:\\ABCD_123.45;1"}),
    "raw": PS1,
    "udf": udf_image({"SYSTEM.CNF": b"BOOT2 = cdrom0:\\ABCD_123.45;1"}),
    "xbox": xdvdfs_volume(("default.xex", "media")),
    "3ds": ncsd(ncch(decrypted=True)),
    "pbp": pbp_image(2, {"DISC_ID": LETTERS + DIGITS}),
    "wii": nintendo_header("ABCE01", "Lantern", wii=True) + bytes(4096),
    "mds": mds_image((MdsTrack(0xAB, 1, 2352, 0, 0),), "*.mdf"),
}
HOT = {name: structure(image) for name, image in BASES.items()}


class TestHostileInput:
    @pytest.mark.parametrize("name", sorted(BASES))
    @QUICK
    @given(mutations=MUTATIONS, cut=CUTS)
    def test_a_corrupted_file_of_any_kind_is_refused_or_read_within_bounds(
        self, name, mutations, cut
    ):
        # Arrange
        image = corrupted(BASES[name], HOT[name], mutations, cut)
        path = Path(f"fuzzed.{name}")

        # Act
        outcome = attempt(lambda source: detect.analyze(path, source), image, HenkanError)

        # Assert
        assert outcome.bounded
