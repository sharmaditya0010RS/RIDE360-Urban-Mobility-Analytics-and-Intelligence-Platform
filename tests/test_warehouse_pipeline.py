
"""Tests for RIDE360 PostgreSQL warehouse engineering.

Unit tests do not require PostgreSQL.
The integration test runs only when the database is reachable.
"""

import csv
from decimal import Decimal
from pathlib import Path
from typing import Literal, cast

import psycopg
import pytest

SOURCE_ROW_KEY = Literal[
    "Date",
    "Time",
    "Booking ID",
    "Booking Status",
    "Customer ID",
    "Vehicle Type",
    "Pickup Location",
    "Drop Location",
    "Avg VTAT",
    "Avg CTAT",
    "Cancelled Rides by Customer",
    "Reason for cancelling by Customer",
    "Cancelled Rides by Driver",
    "Driver Cancellation Reason",
    "Incomplete Rides",
    "Incomplete Rides Reason",
    "Booking Value",
    "Ride Distance",
    "Driver Ratings",
    "Customer Rating",
    "Payment Method",
]

from ride360.warehouse_pipeline import (
    EXPECTED_COLUMNS,
    calculate_sha256,
    count_source_records,
    get_database_config,
    read_source,
)
from ride360.warehouse_validation import (
    PHASE1_BASELINE,
    build_report,
    compare_metrics,
    evaluate_quality_checks,
)


@pytest.fixture
def sample_csv(tmp_path):
    """Create a valid source CSV with repeated Booking IDs."""
    path = tmp_path / "bookings.csv"

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=EXPECTED_COLUMNS,
        )

        writer.writeheader()

        for status in (
            "Completed",
            "Cancelled by Customer",
            "Completed",
        ):
            record = {
                column: ""
                for column in EXPECTED_COLUMNS
            }
            record["Date"] = "2024-01-01"
            record["Time"] = "10:00:00"
            record["Booking ID"] = "DUPLICATE-001"
            record["Booking Status"] = status
            record["Booking Value"] = "500"

            writer.writerow(cast(dict[SOURCE_ROW_KEY, str], record))

    return path


def test_source_schema_has_21_columns():
    assert len(EXPECTED_COLUMNS) == 21
    assert len(set(EXPECTED_COLUMNS)) == 21


def test_csv_reader_preserves_all_records(sample_csv):
    records = list(read_source(sample_csv))

    assert len(records) == 3
    assert [row_number for row_number, _ in records] == [
        2,
        3,
        4,
    ]


def test_csv_reader_preserves_repeated_ids(sample_csv):
    records = list(read_source(sample_csv))

    booking_ids = [
        record["Booking ID"]
        for _, record in records
    ]

    assert booking_ids == [
        "DUPLICATE-001",
        "DUPLICATE-001",
        "DUPLICATE-001",
    ]


def test_source_record_count(sample_csv):
    assert count_source_records(sample_csv) == 3


def test_sha256_is_stable(sample_csv):
    first = calculate_sha256(sample_csv)
    second = calculate_sha256(sample_csv)

    assert first == second
    assert len(first) == 64


def test_sha256_changes_with_content(sample_csv):
    before = calculate_sha256(sample_csv)

    with sample_csv.open(
        "a",
        encoding="utf-8",
    ) as handle:
        handle.write("\n")

    after = calculate_sha256(sample_csv)

    assert before != after


def test_csv_rejects_incorrect_header(tmp_path):
    path = tmp_path / "invalid.csv"

    path.write_text(
        "Booking ID,Booking Status\nA,Completed\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="schema mismatch"):
        list(read_source(path))


def test_csv_rejects_extra_fields(tmp_path):
    path = tmp_path / "extra.csv"

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(EXPECTED_COLUMNS)
        writer.writerow(
            ["value"] * (len(EXPECTED_COLUMNS) + 1)
        )

    with pytest.raises(ValueError, match="Extra CSV fields"):
        list(read_source(path))


def test_csv_rejects_missing_fields(tmp_path):
    path = tmp_path / "missing.csv"

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(EXPECTED_COLUMNS)
        writer.writerow(["value"])

    with pytest.raises(ValueError, match="Missing CSV fields"):
        list(read_source(path))


def test_missing_env_file_is_rejected(tmp_path):
    with pytest.raises(
        FileNotFoundError,
        match="Environment file not found",
    ):
        get_database_config(tmp_path / "missing.env")


def test_missing_database_password_is_rejected(tmp_path):
    env_path = tmp_path / ".env"

    env_path.write_text(
        "POSTGRES_DB=ride360\n"
        "POSTGRES_USER=ride360\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="POSTGRES_PASSWORD missing",
    ):
        get_database_config(env_path)


def test_metric_comparison_passes():
    actual = {
        "total_booking_records": 150000,
        "completed_booking_value_total": Decimal(
            47260574
        ),
    }

    expected = {
        "total_booking_records": 150000,
        "completed_booking_value_total": Decimal(
            47260574
        ),
    }

    results = compare_metrics(actual, expected)

    assert all(result["passed"] for result in results)


def test_metric_comparison_detects_mismatch():
    results = compare_metrics(
        {"completed_bookings": 10},
        {"completed_bookings": 11},
    )

    assert len(results) == 1
    assert results[0]["passed"] is False


def test_quality_checks_pass_with_20_unique_checks():
    rows = [
        {
            "batch_id": 1,
            "check_name": f"check_{number}",
            "passed": True,
        }
        for number in range(20)
    ]

    results = evaluate_quality_checks(rows, [1])

    assert len(results) == 1
    assert results[0]["passed"] is True
    assert results[0]["passed_checks"] == 20


def test_quality_checks_fail_when_one_fails():
    rows = [
        {
            "batch_id": 1,
            "check_name": f"check_{number}",
            "passed": number != 7,
        }
        for number in range(20)
    ]

    results = evaluate_quality_checks(rows, [1])

    assert results[0]["passed"] is False
    assert results[0]["failed_checks"] == 1


def test_quality_checks_fail_when_missing():
    results = evaluate_quality_checks([], [1])

    assert results[0]["passed"] is False
    assert results[0]["total_checks"] == 0


def test_report_fails_without_baseline_comparison():
    rows = [
        {
            "batch_id": 1,
            "check_name": f"check_{number}",
            "passed": True,
        }
        for number in range(20)
    ]

    report = build_report(
        completed_batches=[{"batch_id": 1}],
        sql_checks=rows,
        baseline_comparisons=[],
        source_filename="rideBookings.csv",
        source_sha256="a" * 64,
    )

    assert report["status"] == "FAIL"
    assert report["phase1_baseline_passed"] is False


def test_phase1_baseline_has_expected_metrics():
    assert PHASE1_BASELINE["total_booking_records"] == 150000
    assert PHASE1_BASELINE["completed_bookings"] == 93000
    assert PHASE1_BASELINE["cancelled_bookings"] == 37500
    assert PHASE1_BASELINE["distinct_booking_ids"] == 148767
    assert (
        PHASE1_BASELINE["repeated_booking_id_groups"]
        == 1224
    )


def test_integration_warehouse_reconciliation():
    """Validate the live warehouse if .env and DB are available."""
    project_root = Path(__file__).resolve().parents[1]
    env_path = project_root / ".env"

    if not env_path.is_file():
        pytest.skip("No local PostgreSQL .env available")

    config = get_database_config(env_path)

    try:
        connection = psycopg.connect(**config)
    except psycopg.OperationalError:
        pytest.skip("PostgreSQL is not reachable")

    with connection, connection.cursor() as cursor:
        cursor.execute(
            """
                SELECT
                    total_checks,
                    passed_checks,
                    failed_checks,
                    all_checks_passed
                FROM ride360_audit.warehouse_quality_summary
                WHERE batch_id = 1
                """
        )

        row = cursor.fetchone()

        assert row is not None
        assert row[0] == 20
        assert row[1] == 20
        assert row[2] == 0
        assert row[3] is True
