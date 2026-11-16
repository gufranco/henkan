from types import ModuleType

import pytest

from henkan import doctor
from henkan.version import VERSION


def importer_without(*missing: str):
    def load(name: str) -> ModuleType:
        if name in missing:
            raise ModuleNotFoundError(f"No module named {name!r}", name=name)
        return ModuleType(name)

    return load


def tools(
    *,
    requirements: tuple[str, ...] = (),
    installed: dict[str, doctor.Installed] | None = None,
    chdman: str | None = None,
    banner: str = "",
) -> doctor.Tools:
    return doctor.Tools(
        executable="/opt/python/bin/python3.14",
        requirements=lambda: requirements,
        installed=(installed or {}).get,
        find=lambda name: chdman,
        banner=lambda path: banner,
    )


BANNER = "chdman - MAME Compressed Hunks of Data (CHD) manager {} (unknown)\nUsage:\n"
CHDMAN = "/opt/tools/bin/chdman"


def by_name(report: doctor.DoctorReport) -> dict[str, doctor.Check]:
    return {check.name: check for check in report.checks}


class TestTheReport:
    def test_a_complete_python_on_a_supported_system_is_healthy(self):
        # Arrange
        importer = importer_without()

        # Act
        report = doctor.diagnose(
            importer=importer,
            python=(3, 14, 3),
            system="Linux",
            tools=tools(chdman=CHDMAN, banner=BANNER.format("0.289")),
        )

        # Assert
        checks = by_name(report)
        assert report.healthy is True
        assert list(checks) == ["henkan", "python", "platform", *doctor.CODECS, "chdman"]
        assert checks["henkan"].detail == VERSION
        assert checks["python"].detail == "3.14.3 at /opt/python/bin/python3.14"
        assert {check.status for check in report.checks} == {doctor.CheckStatus.OK}

    def test_a_missing_codec_fails_and_names_what_is_missing(self):
        # Arrange
        importer = importer_without("compression.zstd")

        # Act
        report = doctor.diagnose(importer=importer, python=(3, 14, 3), system="Darwin")

        # Assert
        zstd = by_name(report)["compression.zstd"]
        assert zstd.status is doctor.CheckStatus.FAILED
        assert zstd.detail == "this Python was built without compression.zstd, which henkan needs"
        assert report.healthy is False

    def test_a_python_older_than_the_floor_fails(self):
        # Arrange
        importer = importer_without()

        # Act
        report = doctor.diagnose(
            importer=importer, python=(3, 13, 9), system="Linux", tools=tools()
        )

        # Assert
        python = by_name(report)["python"]
        assert python.status is doctor.CheckStatus.FAILED
        assert python.detail == (
            "3.13.9 at /opt/python/bin/python3.14, older than 3.14, the oldest supported"
        )
        assert report.healthy is False

    def test_an_unsupported_system_is_a_warning_not_a_failure(self):
        # Arrange
        importer = importer_without()

        # Act
        report = doctor.diagnose(importer=importer, python=(3, 14, 3), system="Windows")

        # Assert
        platform = by_name(report)["platform"]
        assert platform.status is doctor.CheckStatus.WARNING
        assert platform.detail.startswith("Windows ")
        assert platform.detail.endswith(", untested: henkan supports Linux and macOS")
        assert report.healthy is True

    def test_an_empty_report_has_no_verdict(self):
        # Arrange
        report = doctor.DoctorReport(())

        # Act
        with pytest.raises(ValueError) as raised:
            _ = report.healthy

        # Assert
        assert str(raised.value) == "nothing was checked, so there is no verdict to give"

    def test_the_running_python_and_system_are_checked_when_none_is_given(self):
        # Arrange
        importer = importer_without()

        # Act
        report = doctor.diagnose(importer=importer)

        # Assert
        checks = by_name(report)
        assert checks["python"].status is doctor.CheckStatus.OK
        assert checks["platform"].status is doctor.CheckStatus.OK


class TestThePackageRows:
    def test_an_installed_package_at_its_pinned_version_is_ok_with_path_and_version(self):
        # Arrange
        installed = {"typer": doctor.Installed("0.29.1", "/opt/site-packages")}
        host = tools(requirements=('typer==0.29.1; extra == "cli"',), installed=installed)

        # Act
        report = doctor.diagnose(importer=importer_without(), tools=host)

        # Assert
        assert by_name(report)["typer"] == doctor.Check(
            "typer", doctor.CheckStatus.OK, "0.29.1 at /opt/site-packages"
        )

    def test_another_version_than_the_pinned_one_is_a_warning_naming_the_tested_one(self):
        # Arrange
        installed = {"lz4": doctor.Installed("4.5.0", "/opt/site-packages")}
        host = tools(requirements=("lz4==4.4.4",), installed=installed)

        # Act
        report = doctor.diagnose(importer=importer_without(), tools=host)

        # Assert
        assert by_name(report)["lz4"] == doctor.Check(
            "lz4", doctor.CheckStatus.WARNING, "4.5.0 at /opt/site-packages, tested with 4.4.4"
        )

    def test_a_package_without_a_pin_is_ok_at_any_version(self):
        # Arrange
        installed = {"xxhash": doctor.Installed("3.6.0", "/opt/site-packages")}
        host = tools(requirements=("xxhash>=3",), installed=installed)

        # Act
        report = doctor.diagnose(importer=importer_without(), tools=host)

        # Assert
        assert by_name(report)["xxhash"].status is doctor.CheckStatus.OK

    def test_a_missing_package_of_an_extra_is_missing_and_names_the_extra(self):
        # Arrange
        host = tools(requirements=('textual==8.0.0 ; extra == "tui"',))

        # Act
        report = doctor.diagnose(importer=importer_without(), tools=host)

        # Assert
        assert by_name(report)["textual"] == doctor.Check(
            "textual", doctor.CheckStatus.MISSING, "not installed; the tui extra provides it"
        )
        assert report.healthy is True

    def test_a_missing_package_henkan_always_needs_fails(self):
        # Arrange
        host = tools(requirements=("cryptography==48.0.0",))

        # Act
        report = doctor.diagnose(importer=importer_without(), tools=host)

        # Assert
        assert by_name(report)["cryptography"] == doctor.Check(
            "cryptography", doctor.CheckStatus.FAILED, "not installed, and henkan needs it"
        )
        assert report.healthy is False

    def test_the_real_environment_lists_the_packages_henkan_declares(self):
        # Arrange
        importer = importer_without()

        # Act
        report = doctor.diagnose(importer=importer)

        # Assert
        typer = by_name(report)["typer"]
        assert typer.status is doctor.CheckStatus.OK
        assert " at /" in typer.detail

    def test_a_package_that_is_not_installed_has_no_version(self):
        # Arrange
        name = "henkan-no-such-package"

        # Act
        found = doctor.installed(name)

        # Assert
        assert found is None

    def test_a_distribution_that_is_not_installed_declares_nothing(self):
        # Arrange
        name = "henkan-no-such-package"

        # Act
        found = doctor.requirements(name)

        # Assert
        assert found == ()


class TestTheChdmanRow:
    @pytest.mark.parametrize("version", ["0.285", "0.289"])
    def test_a_version_inside_the_tested_range_is_ok_with_path_and_version(self, version):
        # Arrange
        host = tools(chdman=CHDMAN, banner=BANNER.format(version))

        # Act
        report = doctor.diagnose(importer=importer_without(), tools=host)

        # Assert
        assert by_name(report)["chdman"] == doctor.Check(
            "chdman", doctor.CheckStatus.OK, f"{version} at {CHDMAN}"
        )

    @pytest.mark.parametrize("version", ["0.284", "0.290", "1.0"])
    def test_a_version_outside_it_is_a_warning_naming_the_tested_range(self, version):
        # Arrange
        host = tools(chdman=CHDMAN, banner=BANNER.format(version))

        # Act
        report = doctor.diagnose(importer=importer_without(), tools=host)

        # Assert
        assert by_name(report)["chdman"] == doctor.Check(
            "chdman",
            doctor.CheckStatus.WARNING,
            f"{version} at {CHDMAN}, outside the tested range 0.285 to 0.289",
        )
        assert report.healthy is True

    def test_a_banner_without_a_version_is_a_warning(self):
        # Arrange
        host = tools(chdman=CHDMAN, banner="something else\n")

        # Act
        report = doctor.diagnose(importer=importer_without(), tools=host)

        # Assert
        assert by_name(report)["chdman"] == doctor.Check(
            "chdman",
            doctor.CheckStatus.WARNING,
            f"{CHDMAN}, version unreadable; tested with 0.285 to 0.289",
        )

    def test_no_chdman_on_the_path_is_missing_and_says_what_provides_it(self):
        # Arrange
        host = tools()

        # Act
        report = doctor.diagnose(importer=importer_without(), tools=host)

        # Assert
        assert by_name(report)["chdman"] == doctor.Check(
            "chdman",
            doctor.CheckStatus.MISSING,
            "not found; CHD files need it: rom-tools in Homebrew, mame-tools on Ubuntu",
        )
        assert report.healthy is True


class TestReadingTheBanner:
    def test_it_returns_what_the_program_prints(self, tmp_path):
        # Arrange
        program = tmp_path / "chdman"
        program.write_text("#!/bin/sh\necho 'manager 0.289 (unknown)'\necho usage >&2\nexit 1\n")
        program.chmod(0o755)

        # Act
        text = doctor.banner(str(program))

        # Assert
        assert text == "manager 0.289 (unknown)\nusage\n"

    def test_a_program_that_cannot_run_prints_nothing(self, tmp_path):
        # Arrange
        program = tmp_path / "chdman"
        program.write_text("not a program")

        # Act
        text = doctor.banner(str(program))

        # Assert
        assert text == ""

    def test_a_program_that_hangs_is_given_up_on(self, tmp_path):
        # Arrange
        program = tmp_path / "chdman"
        program.write_text("#!/bin/sh\nexec sleep 30\n")
        program.chmod(0o755)

        # Act
        text = doctor.banner(str(program), timeout=0.2)

        # Assert
        assert text == ""
