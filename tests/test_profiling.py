
"""Tests for RIDE360 profiling engine."""

import json
from pathlib import Path

import pandas as pd
import pytest

from ride360.profiling import (
    export_profile,
    load_bookings,
    profile_bookings,
    profile_columns,
    profile_numeric,
)


@pytest.fixture
def sample_bookings() -> pd.DataFrame:
    return pd.DataFrame({
        "Booking ID": [
            "B001",
            "B002",
            "B002",
        ],
        "Booking Status": [
            "Completed",
            "Cancelled",
            "Cancelled",
        ],
        "Booking Value": [
            200.0,
            None,
            None,
        ],
    })


def test_column_profile(
    sample_bookings: pd.DataFrame,
) -> None:
    result = profile_columns(
        sample_bookings
    )

    value_row = result.loc[
        result["column"] == "Booking Value"
    ].iloc[0]

    assert value_row["missing_count"] == 2
    assert value_row["non_null_count"] == 1
    assert value_row["missing_pct"] == 66.67


def test_duplicate_detection(
    sample_bookings: pd.DataFrame,
) -> None:
    result = profile_bookings(
        sample_bookings
    )

    assert result["total_rows"] == 3
    assert result["unique_booking_ids"] == 2
    assert result["repeated_booking_id_rows"] == 2
    assert result["extra_booking_id_occurrences"] == 1


def test_numeric_profile(
    sample_bookings: pd.DataFrame,
) -> None:
    result = profile_numeric(
        sample_bookings
    )

    value_row = result.loc[
        result["column"] == "Booking Value"
    ].iloc[0]

    assert value_row["count"] == 1
    assert value_row["mean"] == 200.0


def test_export_reports(
    sample_bookings: pd.DataFrame,
    tmp_path: Path,
) -> None:
    result = export_profile(
        sample_bookings,
        tmp_path,
    )

    assert result["total_rows"] == 3

    expected_files = [
        "column_profile.csv",
        "numeric_profile.csv",
        "duplicate_booking_ids.csv",
        "source_summary.json",
    ]

    for filename in expected_files:
        assert (
            tmp_path / filename
        ).exists()

    summary = json.loads(
        (
            tmp_path / "source_summary.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert summary["unique_booking_ids"] == 2


def test_missing_source(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        FileNotFoundError
    ):
        load_bookings(
            tmp_path / "missing.csv"
        )


def test_missing_required_column() -> None:
    df = pd.DataFrame({
        "Booking ID": ["B001"]
    })

    with pytest.raises(
        ValueError,
        match="Missing required columns",
    ):
        profile_bookings(df)
