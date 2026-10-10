"""Unit tests for the allowlisted report catalog."""
from pathlib import Path

import pytest

from ride360.report_catalog import discover_reports, read_report


def test_discovers_supported_reports(tmp_path: Path):
    directory = tmp_path / "powerbi"
    directory.mkdir()
    (directory / "Ride360.pbix").write_bytes(b"example")
    (directory / "notes.txt").write_text("not a report")
    reports = discover_reports(tmp_path)
    assert len(reports) == 1
    assert reports[0].extension == ".pbix"
    assert read_report(reports[0], tmp_path) == b"example"


def test_does_not_scan_outside_report_folders(tmp_path: Path):
    (tmp_path / "private.pdf").write_bytes(b"private")
    assert discover_reports(tmp_path) == []


def test_blocks_report_outside_root(tmp_path: Path):
    allowed = tmp_path / "allowed"
    other = tmp_path / "other"
    (allowed / "pdfs").mkdir(parents=True)
    (other / "pdfs").mkdir(parents=True)
    (other / "pdfs" / "secret.pdf").write_bytes(b"secret")
    report = discover_reports(other)[0]
    with pytest.raises(ValueError, match="outside"):
        read_report(report, allowed)
