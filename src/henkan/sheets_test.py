from pathlib import Path

import pytest

from henkan import sheets
from henkan.errors import FormatError, RefusalError
from henkan.formats.sheet import TrackType
from henkan.model import DiscClass, Format, Item, Platform
from henkan.source import open_source
from henkan.synthetic_test_support import (
    MdsTrack,
    Tree,
    game_code,
    iso_image,
    mds_image,
    raw_image,
    rng,
)

LETTERS, DIGITS = game_code(rng())
CODE = f"{LETTERS}-{DIGITS}"
PS1: Tree = {"SYSTEM.CNF;1": f"BOOT = cdrom:\\{LETTERS}_{DIGITS[:3]}.{DIGITS[3:]};1".encode()}
DATA = raw_image(iso_image(PS1), 2)
AUDIO = bytes(2352 * 4)
CUE = (
    'FILE "data.bin" BINARY\n  TRACK 01 MODE2/2352\n    INDEX 01 00:00:00\n'
    'FILE "audio.bin" BINARY\n  TRACK 02 AUDIO\n    INDEX 01 00:00:00\n'
)
CCD = "[CloneCD]\nVersion=3\n[Disc]\nSessions=1\n"


def analyzed(path: Path) -> Item | None:
    with open_source(path) as source:
        return sheets.analyze(path, source)


class TestACueSheet:
    def test_its_first_data_track_gives_platform_and_id_and_its_files_the_size(self, tmp_path):
        # Arrange
        (tmp_path / "data.bin").write_bytes(DATA)
        (tmp_path / "audio.bin").write_bytes(AUDIO)
        path = tmp_path / "game.cue"
        path.write_text(CUE)

        # Act
        item = analyzed(path)

        # Assert
        assert item == Item(
            path=path,
            kind=Format.CUE,
            platform=Platform.PS1,
            disc=DiscClass.CD,
            reason="a CUE sheet describes a CD",
            tracks=(TrackType.MODE2_2352, TrackType.AUDIO),
            size=len(DATA) + len(AUDIO),
            files=(path, tmp_path / "data.bin", tmp_path / "audio.bin"),
            game_id=CODE,
        )

    def test_a_data_track_after_audio_is_found_at_its_start(self, tmp_path):
        # Arrange
        (tmp_path / "game.bin").write_bytes(AUDIO + DATA)
        path = tmp_path / "game.cue"
        path.write_text(
            'FILE "game.bin" BINARY\nTRACK 01 AUDIO\nINDEX 01 00:00:00\n'
            "TRACK 02 MODE2/2352\nINDEX 01 00:00:04\n"
        )

        # Act
        item = analyzed(path)

        # Assert
        assert (item.platform, item.game_id) == (Platform.PS1, CODE)

    def test_a_data_track_that_tells_nothing_falls_back_to_the_first_file(self, tmp_path):
        # Arrange
        (tmp_path / "data.bin").write_bytes(DATA)
        (tmp_path / "audio.bin").write_bytes(AUDIO)
        path = tmp_path / "game.cue"
        path.write_text(
            'FILE "data.bin" BINARY\nTRACK 01 AUDIO\nINDEX 01 00:00:00\n'
            'FILE "audio.bin" BINARY\nTRACK 02 MODE2/2336\nINDEX 01 00:00:00\n'
        )

        # Act
        item = analyzed(path)

        # Assert
        assert (item.platform, item.types_known) == (Platform.PS1, False)

    def test_a_disc_no_reader_recognizes_has_no_platform(self, tmp_path):
        # Arrange
        (tmp_path / "audio.bin").write_bytes(AUDIO)
        path = tmp_path / "game.cue"
        path.write_text('FILE "audio.bin" BINARY\nTRACK 01 AUDIO\nINDEX 01 00:00:00\n')

        # Act
        item = analyzed(path)

        # Assert
        assert (item.platform, item.game_id) == (None, "")

    def test_a_file_named_in_another_case_or_with_a_folder_prefix_is_still_found(self, tmp_path):
        # Arrange
        (tmp_path / "Data.BIN").write_bytes(DATA)
        path = tmp_path / "game.cue"
        path.write_text('FILE "C:\\rips\\data.bin" BINARY\nTRACK 01 MODE2/2352\n')

        # Act
        item = analyzed(path)

        # Assert
        assert item.files == (path, tmp_path / "Data.BIN")

    def test_missing_files_are_refused_by_name(self, tmp_path):
        # Arrange
        (tmp_path / "audio.bin").mkdir()
        path = tmp_path / "game.cue"
        path.write_text(CUE + 'FILE "sub/" BINARY\n')

        # Act
        with pytest.raises(RefusalError) as raised:
            analyzed(path)

        # Assert
        assert str(raised.value) == (
            "game.cue names files that are missing: data.bin, audio.bin, sub/"
        )


class TestAGdiSheet:
    def test_it_is_always_dreamcast(self, tmp_path):
        # Arrange
        (tmp_path / "track01.bin").write_bytes(AUDIO)
        (tmp_path / "track02.raw").write_bytes(AUDIO)
        path = tmp_path / "game.gdi"
        path.write_text("2\n1 0 4 2352 track01.bin 0\n2 756 0 2352 track02.raw 0\n")

        # Act
        item = analyzed(path)

        # Assert
        assert (item.kind, item.platform, item.disc, item.tracks) == (
            Format.GDI,
            Platform.DREAMCAST,
            DiscClass.CD,
            (TrackType.MODE1_2352, TrackType.AUDIO),
        )


class TestATocSheet:
    def test_it_claims_no_track_types_and_is_sniffed_from_its_first_file(self, tmp_path):
        # Arrange
        (tmp_path / "data.bin").write_bytes(DATA)
        path = tmp_path / "game.toc"
        path.write_text('CD_ROM_XA\n\nTRACK MODE2_RAW\nDATAFILE "data.bin"\n')

        # Act
        item = analyzed(path)

        # Assert
        assert (item.kind, item.platform, item.tracks, item.types_known) == (
            Format.TOC,
            Platform.PS1,
            (),
            False,
        )


class TestACcdSheet:
    def test_the_image_and_subchannel_files_beside_it_belong_to_it(self, tmp_path):
        # Arrange
        (tmp_path / "game.img").write_bytes(DATA + AUDIO)
        (tmp_path / "game.sub").write_bytes(b"sub")
        path = tmp_path / "game.ccd"
        tracks = f"[TRACK 1]\nMODE=2\nINDEX 1=0\n[TRACK 2]\nMODE=0\nINDEX 1={len(DATA) // 2352}\n"
        path.write_text(CCD + tracks)

        # Act
        item = analyzed(path)

        # Assert
        assert (item.kind, item.platform, item.tracks, item.files) == (
            Format.CCD,
            Platform.PS1,
            (TrackType.MODE2_2352, TrackType.AUDIO),
            (path, tmp_path / "game.img", tmp_path / "game.sub"),
        )

    def test_a_track_the_sheet_gives_no_mode_for_is_typed_from_its_first_sector(self, tmp_path):
        # Arrange
        (tmp_path / "game.img").write_bytes(DATA + AUDIO)
        path = tmp_path / "game.ccd"
        entries = (
            "[Entry 0]\nPoint=1\nControl=0x04\nPLBA=0\n"
            f"[Entry 1]\nPoint=2\nControl=0x04\nPLBA={len(DATA) // 2352}\n"
        )
        path.write_text(CCD + entries)

        # Act
        item = analyzed(path)

        # Assert
        assert item.tracks == (TrackType.MODE2_2352, TrackType.AUDIO)

    def test_an_image_that_is_not_whole_raw_sectors_is_refused(self, tmp_path):
        # Arrange
        (tmp_path / "game.img").write_bytes(DATA + b"x")
        path = tmp_path / "game.ccd"
        path.write_text(CCD + "[TRACK 1]\nMODE=2\nINDEX 1=0\n")

        # Act
        with pytest.raises(FormatError) as raised:
            analyzed(path)

        # Assert
        assert str(raised.value) == "game.img is not made of whole 2352-byte sectors"


class TestAnMdsDescriptor:
    @pytest.mark.parametrize("name", ["game.mdf", "game.img"])
    def test_its_data_file_is_found_by_stem_and_its_tracks_typed_by_stride(self, tmp_path, name):
        # Arrange
        cooked = iso_image(PS1)
        (tmp_path / name).write_bytes(cooked + AUDIO)
        tracks = (
            MdsTrack(0xAA, 1, 2048, 0, 0),
            MdsTrack(0xAB, 2, 2336, 100, len(cooked)),
            MdsTrack(0xA9, 3, 2352, 200, len(cooked)),
        )
        path = tmp_path / "game.mds"
        path.write_bytes(mds_image(tracks, "*.mdf"))

        # Act
        item = analyzed(path)

        # Assert
        assert (item.kind, item.platform, item.tracks, item.files) == (
            Format.MDS,
            Platform.PS1,
            (TrackType.MODE1_2048, TrackType.MODE2_2336, TrackType.AUDIO),
            (path, tmp_path / name),
        )

    def test_a_first_data_track_with_subchannel_sectors_is_not_sniffed(self, tmp_path):
        # Arrange
        (tmp_path / "game.mdf").write_bytes(AUDIO)
        path = tmp_path / "game.mds"
        path.write_bytes(mds_image((MdsTrack(0xAB, 1, 2448, 0, 0),), "*.mdf"))

        # Act
        item = analyzed(path)

        # Assert
        assert (item.platform, item.tracks) == (None, (TrackType.AUDIO,))

    def test_a_missing_data_file_is_refused_by_its_recorded_name(self, tmp_path):
        # Arrange
        path = tmp_path / "game.mds"
        path.write_bytes(mds_image((MdsTrack(0xAB, 1, 2352, 0, 0),), "*.mdf"))

        # Act
        with pytest.raises(RefusalError) as raised:
            analyzed(path)

        # Assert
        assert str(raised.value) == "game.mds names files that are missing: game.mdf"


class TestTellingASheetFromItsContent:
    @pytest.mark.parametrize(
        ("name", "text", "kind"),
        [
            ("a.txt", CUE, Format.CUE),
            ("a.cue", "2\n1 0 4 2352 data.bin 0\n2 9 0 2352 audio.bin 0\n", Format.GDI),
            ("a.cue", 'CD_ROM\nTRACK MODE1_RAW\nFILE "data.bin" 0\n', Format.TOC),
            ("a.cue", 'TRACK AUDIO\nFILE "audio.bin" 0\n', Format.TOC),
            ("a.toc", CUE, Format.CUE),
        ],
    )
    def test_the_content_decides_and_the_extension_does_not(self, tmp_path, name, text, kind):
        # Arrange
        (tmp_path / "data.bin").write_bytes(DATA)
        (tmp_path / "audio.bin").write_bytes(AUDIO)
        path = tmp_path / name
        path.write_text(text)

        # Act
        item = analyzed(path)

        # Assert
        assert item.kind == kind

    def test_text_without_any_marker_is_read_by_its_extension(self, tmp_path):
        # Arrange
        path = tmp_path / "empty.cue"
        path.write_text("REM nothing\n")

        # Act
        with pytest.raises(FormatError) as raised:
            analyzed(path)

        # Assert
        assert str(raised.value) == "not a CUE sheet: it names no file"

    @pytest.mark.parametrize(
        "data",
        [
            b"plain notes\n",
            b"1\nnot a track\n",
            b"\0binary",
            bytes(sheets.SHEET_MAX + 1),
            b"Track 1 is the best song\n",
        ],
    )
    def test_anything_else_is_not_a_sheet(self, tmp_path, data):
        # Arrange
        path = tmp_path / "notes.txt"
        path.write_bytes(data)

        # Act
        item = analyzed(path)

        # Assert
        assert item is None
