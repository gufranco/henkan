import json
from pathlib import Path

from typer.testing import CliRunner

from henkan import doctor
from henkan.cli.main import app, doctor_lines, exit_code
from henkan.synthetic_test_support import game_code, iso_image, pbp_image, raw_image, rng
from henkan.version import VERSION

LETTERS, DIGITS = game_code(rng())
CODE = f"{LETTERS}-{DIGITS}"
PS1 = raw_image(
    iso_image({"SYSTEM.CNF;1": f"BOOT = cdrom:\\{LETTERS}_{DIGITS[:3]}.{DIGITS[3:]};1".encode()}),
    2,
)


def written(folder: Path, name: str, data: bytes) -> str:
    path = folder / name
    path.write_bytes(data)
    return str(path)


RUNNER = CliRunner()


class TestTheVersion:
    def test_it_prints_the_name_and_version(self):
        # Arrange
        args = ["--version"]

        # Act
        result = RUNNER.invoke(app, args)

        # Assert
        assert result.exit_code == 0
        assert result.output == f"henkan {VERSION}\n"


class TestDoctor:
    def test_it_prints_one_line_per_check_and_exits_zero_when_healthy(self):
        # Arrange
        args = ["doctor"]

        # Act
        result = RUNNER.invoke(app, args)

        # Assert
        lines = result.output.splitlines()
        assert result.exit_code == 0
        assert lines[0] == f"henkan             {VERSION}"
        assert [line.split()[0] for line in lines] == [
            "henkan",
            "python",
            "platform",
            *doctor.CODECS,
            "typer",
            "chdman",
        ]

    def test_json_carries_the_verdict_and_every_check(self):
        # Arrange
        args = ["doctor", "--json"]

        # Act
        result = RUNNER.invoke(app, args)

        # Assert
        report = json.loads(result.output)
        assert result.exit_code == 0
        assert report["healthy"] is True
        assert report["checks"][0] == {"name": "henkan", "status": "ok", "detail": VERSION}

    def test_a_check_that_is_not_ok_carries_its_status(self):
        # Arrange
        report = doctor.DoctorReport(
            (
                doctor.Check("python", doctor.CheckStatus.FAILED, "3.13.9"),
                doctor.Check("lzma", doctor.CheckStatus.MISSING, "absent"),
            )
        )

        # Act
        lines = doctor_lines(report)

        # Assert
        assert lines == [
            "python             3.13.9 [failed]",
            "lzma               absent [missing]",
        ]

    def test_a_failed_check_makes_the_exit_code_one(self):
        # Arrange
        report = doctor.DoctorReport((doctor.Check("python", doctor.CheckStatus.FAILED, "x"),))

        # Act
        code = exit_code(report)

        # Assert
        assert code == 1

    def test_with_no_command_it_shows_the_help(self):
        # Arrange
        args: list[str] = []

        # Act
        result = RUNNER.invoke(app, args)

        # Assert
        assert "doctor" in result.output


class TestInfo:
    def test_it_prints_what_each_file_is_and_exits_zero(self, tmp_path):
        # Arrange
        path = written(tmp_path, "game.bin", PS1)

        # Act
        result = RUNNER.invoke(app, ["info", path])

        # Assert
        assert result.exit_code == 0
        assert result.stdout.splitlines()[:5] == [
            path,
            "  kind      bin",
            "  platform  PS1",
            "  disc      CD: raw CD sectors make a CD whatever the size",
            f"  id        {CODE}",
        ]

    def test_a_refused_file_is_explained_on_stderr_and_the_exit_code_is_one(self, tmp_path):
        # Arrange
        good = written(tmp_path, "game.bin", PS1)
        empty = written(tmp_path, "empty.iso", b"")

        # Act
        result = RUNNER.invoke(app, ["info", good, empty])

        # Assert
        assert result.exit_code == 1
        assert result.stdout.splitlines()[0] == good
        assert result.stderr == "refused: empty.iso is empty\n"

    def test_only_refusals_print_nothing_on_stdout(self, tmp_path):
        # Arrange
        empty = written(tmp_path, "empty.iso", b"")

        # Act
        result = RUNNER.invoke(app, ["info", empty])

        # Assert
        assert (result.exit_code, result.stdout) == (1, "")

    def test_json_carries_items_refusals_and_notes(self, tmp_path):
        # Arrange
        data = written(tmp_path, "game.bin", PS1)
        sheet = written(tmp_path, "game.cue", b'FILE "game.bin" BINARY\nTRACK 01 MODE2/2352\n')
        empty = written(tmp_path, "empty.iso", b"")

        # Act
        result = RUNNER.invoke(app, ["info", "--json", data, sheet, empty])

        # Assert
        found = json.loads(result.stdout)
        assert result.exit_code == 1
        assert [(item["path"], item["platform"], item["id"]) for item in found["items"]] == [
            (sheet, "PS1", CODE)
        ]
        assert found["refused"] == [{"path": empty, "reason": "empty.iso is empty"}]
        assert found["notes"] == ["game.bin is part of game.cue"]
        assert result.stderr == (
            "note: game.bin is part of game.cue\nrefused: empty.iso is empty\n"
        )


class TestList:
    def test_it_prints_each_target_with_the_default_marked(self, tmp_path):
        # Arrange
        path = written(tmp_path, "game.bin", PS1)

        # Act
        result = RUNNER.invoke(app, ["list", path])

        # Assert
        assert result.exit_code == 0
        assert result.stdout.splitlines() == [
            f"{path}  PS1  CD  {len(PS1):,} bytes",
            "  * chd",
            "    iso",
            "    cso",
            "    zso",
            "    cso2",
            "    pbp",
            "    vcd",
            "    cdi",
            "    cue-ecc",
            "    ecm",
        ]

    def test_json_names_the_default(self, tmp_path):
        # Arrange
        path = written(tmp_path, "game.bin", PS1)

        # Act
        result = RUNNER.invoke(app, ["list", "--json", path])

        # Assert
        found = json.loads(result.stdout)
        assert (found["items"][0]["default"], found["items"][0]["targets"][:2]) == (
            "chd",
            ["chd", "iso"],
        )


class TestConvert:
    def test_a_dry_run_names_each_step_and_the_temporary_space(self, tmp_path):
        # Arrange
        image = pbp_image(1, {"DISC_ID": LETTERS + DIGITS})
        path = written(tmp_path, "game.pbp", image)

        # Act
        result = RUNNER.invoke(app, ["convert", path, "--to", "cdi", "--dry-run"])

        # Assert
        size = len(image) * 8 // 5
        assert result.exit_code == 0
        assert result.stdout.splitlines() == [
            f"{path} to cdi",
            f"  1. pbp to cue, kept in a temporary folder: {size:,} bytes",
            "  2. cue to cdi",
            f"  temporary space: {size:,} bytes",
            f"  expected output: {size:,} bytes",
        ]

    def test_a_dry_run_as_json_carries_the_plan(self, tmp_path):
        # Arrange
        path = written(tmp_path, "game.pbp", pbp_image(1, {"DISC_ID": LETTERS + DIGITS}))

        # Act
        result = RUNNER.invoke(app, ["convert", path, "--dry-run", "--json"])

        # Assert
        found = json.loads(result.stdout)
        assert [(plan["target"], len(plan["steps"])) for plan in found["plans"]] == [("chd", 2)]

    def test_a_target_the_file_cannot_become_is_refused_with_exit_one(self, tmp_path):
        # Arrange
        path = written(tmp_path, "game.pbp", pbp_image(1, {"DISC_ID": LETTERS + DIGITS}))

        # Act
        result = RUNNER.invoke(app, ["convert", path, "--to", "rvz", "--dry-run"])

        # Assert
        assert result.exit_code == 1
        assert result.stderr == (
            "refused: game.pbp cannot become rvz; it can become: chd, cue, art, vcd, cdi, cue-ecc\n"
        )

    def test_a_name_that_is_no_target_exits_two(self, tmp_path):
        # Arrange
        path = written(tmp_path, "game.pbp", pbp_image(1, {"DISC_ID": LETTERS + DIGITS}))

        # Act
        result = RUNNER.invoke(app, ["convert", path, "--to", "mp3", "--dry-run"])

        # Assert
        assert result.exit_code == 2
        assert result.stderr.startswith("'mp3' is not a target; the targets are: 3dsx, art, ")

    def test_without_dry_run_it_says_this_version_only_plans(self, tmp_path):
        # Arrange
        path = written(tmp_path, "game.pbp", pbp_image(1, {"DISC_ID": LETTERS + DIGITS}))

        # Act
        result = RUNNER.invoke(app, ["convert", path, "--to", "chd"])

        # Assert
        assert result.exit_code == 1
        assert result.stderr == (
            "this version of henkan plans conversions and does not run them: add --dry-run\n"
        )
