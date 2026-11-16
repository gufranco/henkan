from pathlib import Path

from henkan import gather
from henkan.model import Format, Platform
from henkan.synthetic_test_support import MdsTrack, game_code, iso_image, mds_image, raw_image, rng

LETTERS, DIGITS = game_code(rng())
PS1 = raw_image(
    iso_image({"SYSTEM.CNF;1": f"BOOT = cdrom:\\{LETTERS}_{DIGITS[:3]}.{DIGITS[3:]};1".encode()}),
    2,
)
CUE = b'FILE "game.bin" BINARY\nTRACK 01 MODE2/2352\nINDEX 01 00:00:00\n'
MDS = mds_image((MdsTrack(0xAB, 1, 2352, 0, 0),), "*.mdf")


def written(folder: Path, name: str, data: bytes) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_bytes(data)
    return path


def kinds(found: gather.Gathered) -> list[tuple[str, Format]]:
    return [(item.path.name, item.kind) for item in found.items]


class TestGatheringNamedFiles:
    def test_each_file_becomes_an_item_and_a_bad_one_a_refusal(self, tmp_path):
        # Arrange
        image = written(tmp_path, "game.iso", iso_image({"README.TXT;1": b"x"}))
        empty = written(tmp_path, "empty.iso", b"")
        notes = written(tmp_path, "notes.txt", b"words\n")

        # Act
        found = gather.gather([image, empty, notes])

        # Assert
        assert kinds(found) == [("game.iso", Format.ISO)]
        assert found.refused == (
            gather.Refused(empty, "empty.iso is empty"),
            gather.Refused(notes, "notes.txt is not a kind of file henkan converts"),
        )

    def test_the_same_path_named_twice_is_one_item(self, tmp_path):
        # Arrange
        image = written(tmp_path, "game.iso", iso_image({"README.TXT;1": b"x"}))

        # Act
        found = gather.gather([image, image])

        # Assert
        assert kinds(found) == [("game.iso", Format.ISO)]

    def test_a_file_its_sheet_covers_is_noted_as_part_of_that_sheet(self, tmp_path):
        # Arrange
        data = written(tmp_path, "game.bin", PS1)
        sheet = written(tmp_path, "game.cue", CUE)

        # Act
        found = gather.gather([data, sheet])

        # Assert
        assert kinds(found) == [("game.cue", Format.CUE)]
        assert found.notes == ("game.bin is part of game.cue",)

    def test_a_stand_in_and_what_it_stands_for_are_one_item(self, tmp_path):
        # Arrange
        data = written(tmp_path, "game.mdf", PS1)
        sheet = written(tmp_path, "game.mds", MDS)

        # Act
        found = gather.gather([data, sheet])

        # Assert
        assert kinds(found) == [("game.mds", Format.MDS)]
        assert found.notes == ("game.mdf is part of game.mds",)

    def test_a_named_mdf_without_its_mds_is_refused_with_the_reason(self, tmp_path):
        # Arrange
        data = written(tmp_path, "game.mdf", PS1)

        # Act
        found = gather.gather([data])

        # Assert
        assert found.refused == (
            gather.Refused(
                data,
                "game.mdf holds track data only and cannot be read without its MDS descriptor",
                orphan=True,
            ),
        )
        assert found.notes == ()


class TestGatheringAFolder:
    def test_a_game_folder_is_taken_whole(self, tmp_path):
        # Arrange
        written(tmp_path / "Game", "default.xex", b"x")
        written(tmp_path / "Game" / "media", "extra.iso", iso_image({"A.TXT;1": b"x"}))

        # Act
        found = gather.gather([tmp_path / "Game"])

        # Assert
        assert [(item.path.name, item.platform) for item in found.items] == [
            ("Game", Platform.XBOX_360)
        ]

    def test_any_other_folder_is_walked_at_every_depth_in_path_order(self, tmp_path):
        # Arrange
        written(tmp_path / "b", "game.bin", PS1)
        written(tmp_path / "b", "game.cue", CUE)
        written(tmp_path / "a" / "deep", "disc.iso", iso_image({"A.TXT;1": b"x"}))
        written(tmp_path / "a" / "Xbox", "default.xbe", b"x")
        written(tmp_path, "notes.txt", b"words\n")
        written(tmp_path, "broken.iso", b"")

        # Act
        found = gather.gather([tmp_path])

        # Assert
        assert kinds(found) == [
            ("Xbox", Format.FOLDER),
            ("disc.iso", Format.ISO),
            ("game.cue", Format.CUE),
        ]
        assert found.refused == (gather.Refused(tmp_path / "broken.iso", "broken.iso is empty"),)
        assert found.notes == ()

    def test_system_folders_links_and_henkans_own_temporary_folders_are_skipped(self, tmp_path):
        # Arrange
        image = iso_image({"A.TXT;1": b"x"})
        written(tmp_path / "$Recycle.Bin", "old.iso", image)
        written(tmp_path / "System Volume Information", "old.iso", image)
        written(tmp_path / ".henkan-part", "half.iso", image)
        kept = written(tmp_path / "games", "disc.iso", image)
        (tmp_path / "games" / "link.iso").symlink_to(kept)

        # Act
        found = gather.gather([tmp_path])

        # Assert
        assert [item.path for item in found.items] == [kept]

    def test_mdf_files_without_a_descriptor_are_left_out_and_counted(self, tmp_path):
        # Arrange
        written(tmp_path, "one.mdf", PS1)
        written(tmp_path, "two.mdf", PS1)
        written(tmp_path, "disc.iso", iso_image({"A.TXT;1": b"x"}))

        # Act
        found = gather.gather([tmp_path])

        # Assert
        assert (kinds(found), found.refused) == ([("disc.iso", Format.ISO)], ())
        assert found.notes == (
            "2 MDF files left out: an MDF holds track data only and cannot be read without its "
            "MDS descriptor",
        )

    def test_a_folder_with_nothing_to_convert_is_refused_after_every_folder_was_searched(
        self, tmp_path
    ):
        # Arrange
        folder = tmp_path / "photos"
        written(folder / "2024", "notes.txt", b"words\n")

        # Act
        found = gather.gather([folder])

        # Assert
        assert found.refused == (gather.Refused(folder, "photos holds nothing henkan can convert"),)

    def test_a_folder_with_more_entries_than_the_limit_is_refused(self, tmp_path):
        # Arrange
        folder = tmp_path / "many"
        for index in range(3):
            written(folder, f"{index}.txt", b"x")

        # Act
        found = gather.gather([folder], limit=2)

        # Assert
        assert found.refused == (gather.Refused(folder, "many holds more than 2 entries"),)
