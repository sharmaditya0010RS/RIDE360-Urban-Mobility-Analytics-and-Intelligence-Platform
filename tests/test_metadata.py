
"""Tests for RIDE360 data dictionary and KPI contracts."""

import json

import pandas as pd
import pytest

from ride360.metadata import (
    DATA_DICTIONARY,
    KPI_CONTRACTS,
    calculate_record_kpis,
    export_metadata,
    validate_metadata,
    validate_source_schema,
)


@pytest.fixture
def sample_bookings() -> pd.DataFrame:
    columns = [item["column_name"] for item in DATA_DICTIONARY]

    df = pd.DataFrame(
        [{column: None for column in columns} for _ in range(5)]
    )

    df["Booking ID"] = ["B001", "B002", "B002", "B003", "B004"]
    df["Booking Status"] = [
        "Completed",
        "Completed",
        "Cancelled by Customer",
        "Cancelled by Driver",
        "Incomplete",
    ]
    df["Booking Value"] = [100, 200, None, None, None]

    return df


def test_dictionary_has_21_unique_columns() -> None:
    names = [item["column_name"] for item in DATA_DICTIONARY]

    assert len(names) == 21
    assert len(set(names)) == 21


def test_contract_ids_are_unique() -> None:
    ids = [item["kpi_id"] for item in KPI_CONTRACTS]

    assert len(ids) == 10
    assert len(ids) == len(set(ids))


def test_metadata_is_valid() -> None:
    validate_metadata()


def test_matching_schema_passes(sample_bookings: pd.DataFrame) -> None:
    result = validate_source_schema(sample_bookings)

    assert result["status"] == "PASS"
    assert result["expected_columns"] == 21
    assert result["missing_columns"] == []
    assert result["unexpected_columns"] == []


def test_missing_schema_column_fails(
    sample_bookings: pd.DataFrame,
) -> None:
    invalid = sample_bookings.drop(columns=["Payment Method"])

    result = validate_source_schema(invalid)

    assert result["status"] == "FAIL"
    assert result["missing_columns"] == ["Payment Method"]


def test_unexpected_schema_column_fails(
    sample_bookings: pd.DataFrame,
) -> None:
    sample_bookings["Unexpected"] = 1

    result = validate_source_schema(sample_bookings)

    assert result["status"] == "FAIL"
    assert result["unexpected_columns"] == ["Unexpected"]


def test_record_counts_preserve_duplicate_ids(
    sample_bookings: pd.DataFrame,
) -> None:
    result = calculate_record_kpis(sample_bookings)

    assert result["booking_records"] == 5
    assert result["distinct_booking_ids"] == 4
    assert result["completed_records"] == 2


def test_record_rates(sample_bookings: pd.DataFrame) -> None:
    result = calculate_record_kpis(sample_bookings)

    assert result["completion_rate_pct"] == 40.0
    assert result["customer_cancellation_rate_pct"] == 20.0
    assert result["driver_cancellation_rate_pct"] == 20.0
    assert result["overall_cancellation_rate_pct"] == 40.0
    assert result["incomplete_rate_pct"] == 20.0
    assert result["no_driver_found_rate_pct"] == 0.0


def test_completed_booking_value_is_provisional(
    sample_bookings: pd.DataFrame,
) -> None:
    result = calculate_record_kpis(sample_bookings)

    assert result["completed_booking_value"] == 300.0
    assert result["completed_booking_value_status"] == "provisional"


def test_empty_dataset_rates_are_null(
    sample_bookings: pd.DataFrame,
) -> None:
    result = calculate_record_kpis(sample_bookings.iloc[:0])

    assert result["booking_records"] == 0
    assert result["completion_rate_pct"] is None
    assert result["completed_booking_value"] is None


def test_missing_kpi_column_raises(
    sample_bookings: pd.DataFrame,
) -> None:
    invalid = sample_bookings.drop(columns=["Booking Status"])

    with pytest.raises(ValueError, match="Missing KPI columns"):
        calculate_record_kpis(invalid)


def test_kpi_calculation_does_not_modify_source(
    sample_bookings: pd.DataFrame,
) -> None:
    original = sample_bookings.copy(deep=True)

    calculate_record_kpis(sample_bookings)

    pd.testing.assert_frame_equal(sample_bookings, original)


def test_metadata_export(
    sample_bookings: pd.DataFrame,
    tmp_path,
) -> None:
    summary = export_metadata(sample_bookings, tmp_path)

    assert summary["schema"]["status"] == "PASS"
    assert summary["dictionary_columns"] == 21
    assert summary["kpi_contracts"] == 10

    for filename in (
        "data_dictionary.csv",
        "kpi_contracts.csv",
        "metadata_summary.json",
    ):
        assert (tmp_path / filename).is_file()

    saved = json.loads(
        (tmp_path / "metadata_summary.json").read_text(
            encoding="utf-8"
        )
    )

    assert saved["kpis"]["distinct_booking_ids"] == 4
