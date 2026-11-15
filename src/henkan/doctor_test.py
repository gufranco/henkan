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


def by_name(report: doctor.DoctorReport) -> dict[str, doctor.Check]:
    return {check.name: check for check in report.checks}


class TestTheReport:
    def test_a_complete_python_on_a_supported_system_is_healthy(self):
        # Arrange
        importer = importer_without()

        # Act
        report = doctor.diagnose(importer=importer, python=(3, 14, 3), system="Linux")

        # Assert
        checks = by_name(report)
        assert report.healthy is True
        assert list(checks) == ["henkan", "python", "platform", *doctor.CODECS]
        assert checks["henkan"].detail == VERSION
        assert checks["python"].detail == "3.14.3"
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
        report = doctor.diagnose(importer=importer, python=(3, 13, 9), system="Linux")

        # Assert
        python = by_name(report)["python"]
        assert python.status is doctor.CheckStatus.FAILED
        assert python.detail == "3.13.9, older than 3.14, the oldest supported"
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
