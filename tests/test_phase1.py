
"""Integration and contract tests for Phase 1 orchestration."""

import json
from pathlib import Path

import pandas as pd
import pytest

from ride360 import phase1


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        (["PASS"], "PASS"),
        (["PASS", "PASS"], "PASS"),
        (["PASS", "WARN"], "WARN"),
        (["WARN", "FAIL"], "FAIL"),
        (["FAIL", "PASS"], "FAIL"),
    ],
)
def test_combined_status(
    statuses: list[str],
    expected: str,
) -> None:
    assert phase1.combined_status(statuses) == expected


def test_empty_statuses_rejected() -> None:
    with pytest.raises(ValueError, match="At least one"):
        phase1.combined_status([])


def test_unknown_status_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown"):
        phase1.combined_status(["PASS", "UNKNOWN"])


def test_manifest_preserves_warning() -> None:
    layers = {
        "structural": {"status": "WARN"},
        "business": {"status": "PASS"},
        "events": {"status": "PASS"},
        "metadata": {"status": "PASS"},
    }

    manifest = phase1.build_manifest(
        source=Path("sample.csv"),
        rows=150,
        columns=21,
        layers=layers,
        kpis={"booking_records": 150},
    )

    assert manifest["status"] == "WARN"
    assert manifest["source_rows"] == 150
    assert manifest["policies"]["automatic_deduplication"] is False
    assert manifest["policies"]["booking_grain_approved"] is False


def test_missing_layer_rejected() -> None:
    with pytest.raises(ValueError, match="Missing validation layers"):
        phase1.build_manifest(
            source=Path("sample.csv"),
            rows=1,
            columns=21,
            layers={"structural": {"status": "PASS"}},
            kpis={},
        )


def test_full_orchestration_with_mocked_reports(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify wiring without depending on the 150k-row CSV."""
    sample = pd.DataFrame(
        {
            "Booking ID": ["B001", "B002"],
            "Booking Status": ["Completed", "Incomplete"],
        }
    )

    monkeypatch.setattr(
        phase1,
        "load_bookings",
        lambda source: sample.copy(deep=True),
    )

    def write_report(filename: str, payload: dict):
        def exporter(df: pd.DataFrame, directory: Path) -> None:
            directory.mkdir(parents=True, exist_ok=True)
            (directory / filename).write_text(
                json.dumps(payload),
                encoding="utf-8",
            )

        return exporter

    monkeypatch.setattr(
        phase1,
        "export_profile",
        lambda df, directory: directory.mkdir(
            parents=True, exist_ok=True
        ),
    )

    monkeypatch.setattr(
        phase1,
        "export_quality",
        write_report(
            "quality_summary.json",
            {"status": "WARN"},
        ),
    )

    monkeypatch.setattr(
        phase1,
        "export_business_rules",
        write_report(
            "business_summary.json",
            {"status": "PASS"},
        ),
    )

    monkeypatch.setattr(
        phase1,
        "export_event_rules",
        write_report(
            "event_summary.json",
            {"status": "PASS"},
        ),
    )

    monkeypatch.setattr(
        phase1,
        "export_metadata",
        write_report(
            "metadata_summary.json",
            {
                "schema": {"status": "PASS"},
                "kpis": {
                    "booking_records": 2,
                    "distinct_booking_ids": 2,
                },
            },
        ),
    )

    output = tmp_path / "reports"

    result = phase1.run_phase1(
        tmp_path / "sample.csv",
        output,
    )

    assert result["status"] == "WARN"
    assert result["source_rows"] == 2
    assert result["source_columns"] == 2
    assert result["kpis"]["booking_records"] == 2

    manifest_path = output / "phase1_manifest.json"
    assert manifest_path.is_file()

    saved = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    assert saved["status"] == "WARN"
    assert len(saved["layers"]) == 4
