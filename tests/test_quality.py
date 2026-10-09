
"""Automated tests for RIDE360 quality validation."""

import json

import pandas as pd

from ride360.quality import (
    assess_quality,
    export_quality,
)


def sample_data() -> pd.DataFrame:
    """Create a small valid booking dataset."""
    return pd.DataFrame({
        "Date": ["2024-01-01", "2024-01-02"],
        "Time": ["10:00:00", "11:00:00"],
        "Booking ID": ["B001", "B002"],
        "Booking Status": [
            "Completed",
            "Incomplete",
        ],
        "Customer ID": ["C001", "C002"],
        "Vehicle Type": ["Auto", "Bike"],
        "Pickup Location": ["A", "B"],
        "Drop Location": ["C", "D"],
        "Booking Value": [250.0, None],
        "Ride Distance": [5.0, None],
        "Driver Ratings": [4.5, None],
        "Customer Rating": [4.0, None],
    })


def test_valid_data_passes():
    rules, conflicts, summary = assess_quality(
        sample_data()
    )

    assert summary["status"] == "PASS"
    assert summary["errors"] == 0
    assert len(conflicts) == 0
    assert (rules["result"] == "PASS").all()


def test_invalid_status_fails():
    df = sample_data()
    df.loc[0, "Booking Status"] = "Unknown"

    _, _, summary = assess_quality(df)

    assert summary["status"] == "FAIL"
    assert summary["errors"] >= 1


def test_negative_booking_value_fails():
    df = sample_data()
    df.loc[0, "Booking Value"] = -100.0

    rules, _, summary = assess_quality(df)

    assert summary["status"] == "FAIL"

    result = rules.loc[
        rules["rule"]
        == "nonnegative_numeric:Booking Value"
    ].iloc[0]

    assert result["failed_rows"] == 1


def test_invalid_rating_fails():
    df = sample_data()
    df.loc[0, "Driver Ratings"] = 6.0

    _, _, summary = assess_quality(df)

    assert summary["status"] == "FAIL"


def test_duplicate_id_warns():
    df = sample_data()
    df.loc[1, "Booking ID"] = "B001"

    _, conflicts, summary = assess_quality(df)

    assert summary["status"] == "WARN"
    assert summary["repeated_id_groups"] == 1
    assert summary["conflicting_id_groups"] == 1
    assert len(conflicts) == 1


def test_missing_required_column_fails():
    df = sample_data().drop(
        columns=["Booking ID"]
    )

    _, _, summary = assess_quality(df)

    assert summary["status"] == "FAIL"
    assert "Booking ID" in summary["missing_columns"]


def test_invalid_date_fails():
    df = sample_data()
    df.loc[0, "Date"] = "not-a-date"

    _, _, summary = assess_quality(df)

    assert summary["status"] == "FAIL"


def test_export_reports(tmp_path):
    summary = export_quality(
        sample_data(),
        tmp_path,
    )

    assert summary["status"] == "PASS"

    expected = [
        "quality_rules.csv",
        "duplicate_conflicts.csv",
        "quality_summary.json",
        "quality_report.html",
    ]

    for filename in expected:
        assert (tmp_path / filename).exists()

    saved = json.loads(
        (
            tmp_path / "quality_summary.json"
        ).read_text(encoding="utf-8")
    )

    assert saved["status"] == "PASS"

    html_content = (
        tmp_path / "quality_report.html"
    ).read_text(encoding="utf-8")

    assert "RIDE360" in html_content
    assert "<table>" in html_content
