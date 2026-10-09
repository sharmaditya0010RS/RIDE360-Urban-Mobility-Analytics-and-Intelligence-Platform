
"""RIDE360 warehouse quality and reconciliation runner.

Run:
    python -m ride360.warehouse_validation

The runner:
- Reads PostgreSQL configuration from .env.
- Checks every completed ingestion batch.
- Validates SQL warehouse reconciliation results.
- Compares the original CSV batch against Phase 1 KPIs.
- Writes a JSON validation report.
- Returns a nonzero exit code on validation failure.
"""

import argparse
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import psycopg

from ride360.warehouse_pipeline import (
    DEFAULT_ENV,
    PROJECT_ROOT,
    calculate_sha256,
    get_database_config,
)

DEFAULT_REPORT = (
    PROJECT_ROOT
    / "reports"
    / "generated"
    / "warehouse"
    / "validation_report.json"
)

DEFAULT_SOURCE = (
    PROJECT_ROOT / "data" / "raw" / "rideBookings.csv"
)

# Phase 1 verified reference values for rideBookings.csv.
# These values are source-specific, not universal business rules.
PHASE1_BASELINE = {
    "total_booking_records": 150000,
    "completed_bookings": 93000,
    "cancelled_bookings": 37500,
    "customer_cancelled_bookings": 10500,
    "driver_cancelled_bookings": 27000,
    "incomplete_bookings": 9000,
    "no_driver_found_bookings": 10500,
    "unknown_status_bookings": 0,
    "distinct_booking_ids": 148767,
    "completed_booking_value_total": Decimal(47260574),
    "completion_rate_pct": Decimal("62.00"),
    "cancellation_rate_pct": Decimal("25.00"),
    "repeated_booking_id_groups": 1224,
    "records_in_repeated_groups": 2457,
    "extra_booking_id_occurrences": 1233,
}

KPI_COLUMNS = (
    "total_booking_records",
    "completed_bookings",
    "cancelled_bookings",
    "customer_cancelled_bookings",
    "driver_cancelled_bookings",
    "incomplete_bookings",
    "no_driver_found_bookings",
    "unknown_status_bookings",
    "distinct_booking_ids",
    "completed_booking_value_total",
    "completion_rate_pct",
    "cancellation_rate_pct",
)

DUPLICATION_COLUMNS = (
    "repeated_booking_id_groups",
    "records_in_repeated_groups",
    "extra_booking_id_occurrences",
)


def serialize_value(value):
    """Convert database values into JSON-compatible values."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def fetch_all_as_dicts(connection, query, params=None):
    """Return SQL results as dictionaries."""
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        columns = [
            column.name for column in cursor.description
        ]
        return [
            dict(zip(columns, row, strict=True))
            for row in cursor.fetchall()
        ]


def fetch_quality_checks(connection):
    """Retrieve all completed-batch quality checks."""
    return fetch_all_as_dicts(
        connection,
        """
        SELECT
            batch_id,
            check_name,
            passed,
            expected_value,
            actual_value,
            check_status
        FROM ride360_audit.warehouse_quality_checks
        ORDER BY batch_id, check_name
        """,
    )


def fetch_completed_batches(connection):
    """Retrieve the completed source batch registry."""
    return fetch_all_as_dicts(
        connection,
        """
        SELECT
            batch_id,
            source_filename,
            source_sha256,
            source_record_count,
            loaded_record_count,
            batch_status
        FROM ride360_audit.ingestion_batches
        WHERE batch_status = 'COMPLETED'
        ORDER BY batch_id
        """,
    )


def fetch_kpis(connection, batch_id):
    """Retrieve executive KPI values for a batch."""
    return fetch_all_as_dicts(
        connection,
        """
        SELECT
            total_booking_records,
            completed_bookings,
            cancelled_bookings,
            customer_cancelled_bookings,
            driver_cancelled_bookings,
            incomplete_bookings,
            no_driver_found_bookings,
            unknown_status_bookings,
            distinct_booking_ids,
            completed_booking_value_total,
            completion_rate_pct,
            cancellation_rate_pct
        FROM ride360_analytics.executive_kpis
        WHERE batch_id = %s
        """,
        (batch_id,),
    )


def fetch_duplication_metrics(connection, batch_id):
    """Retrieve repeated Booking ID metrics."""
    return fetch_all_as_dicts(
        connection,
        """
        SELECT
            repeated_booking_id_groups,
            records_in_repeated_groups,
            extra_booking_id_occurrences
        FROM ride360_analytics.booking_id_duplication_summary
        WHERE batch_id = %s
        """,
        (batch_id,),
    )


def compare_metrics(actual, expected):
    """Return detailed results for a metric comparison."""
    results = []

    for metric, expected_value in expected.items():
        actual_value = actual.get(metric)

        results.append(
            {
                "metric": metric,
                "expected": serialize_value(expected_value),
                "actual": serialize_value(actual_value),
                "passed": actual_value == expected_value,
            }
        )

    return results


def evaluate_quality_checks(rows, batch_ids):
    """Validate coverage and outcome of SQL checks."""
    checks_by_batch = {
        batch_id: [] for batch_id in batch_ids
    }

    for row in rows:
        batch_id = row["batch_id"]
        if batch_id in checks_by_batch:
            checks_by_batch[batch_id].append(row)

    results = []

    for batch_id, batch_rows in checks_by_batch.items():
        names = [row["check_name"] for row in batch_rows]

        passed = (
            len(batch_rows) == 20
            and len(set(names)) == 20
            and all(row["passed"] is True for row in batch_rows)
        )

        results.append(
            {
                "batch_id": batch_id,
                "total_checks": len(batch_rows),
                "passed_checks": sum(
                    row["passed"] is True
                    for row in batch_rows
                ),
                "failed_checks": sum(
                    row["passed"] is not True
                    for row in batch_rows
                ),
                "passed": passed,
                "checks": [
                    {
                        key: serialize_value(value)
                        for key, value in row.items()
                    }
                    for row in batch_rows
                ],
            }
        )

    return results


def build_report(
    completed_batches,
    sql_checks,
    baseline_comparisons,
    source_filename,
    source_sha256,
):
    """Construct a machine-readable validation report."""
    batch_ids = [
        row["batch_id"] for row in completed_batches
    ]

    sql_results = evaluate_quality_checks(
        sql_checks,
        batch_ids,
    )

    sql_passed = (
        bool(completed_batches)
        and all(row["passed"] for row in sql_results)
    )

    baseline_passed = (
        bool(baseline_comparisons)
        and all(
            row["passed"]
            for row in baseline_comparisons
        )
    )

    overall_passed = sql_passed and baseline_passed

    return {
        "project": "RIDE360",
        "validation": "PostgreSQL Warehouse Quality",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "status": "PASS" if overall_passed else "FAIL",
        "source_filename": source_filename,
        "source_sha256": source_sha256,
        "completed_batches": len(completed_batches),
        "sql_quality_passed": sql_passed,
        "phase1_baseline_passed": baseline_passed,
        "sql_quality_results": sql_results,
        "phase1_baseline_comparisons": baseline_comparisons,
    }


def write_report(path, report):
    """Persist the validation report as JSON."""
    path = Path(path)
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def run_validation(
    env_path=DEFAULT_ENV,
    source_path=DEFAULT_SOURCE,
    report_path=DEFAULT_REPORT,
):
    """Run warehouse checks and Phase 1 reconciliation."""
    source_path = Path(source_path)

    if not source_path.is_file():
        raise FileNotFoundError(
            f"Source CSV not found: {source_path}"
        )

    source_sha256 = calculate_sha256(source_path)
    source_filename = source_path.name

    config = get_database_config(Path(env_path))

    with psycopg.connect(**config) as connection:
        completed_batches = fetch_completed_batches(
            connection
        )
        sql_checks = fetch_quality_checks(connection)

        matching_batches = [
            row
            for row in completed_batches
            if row["source_sha256"] == source_sha256
            and row["source_filename"] == source_filename
        ]

        baseline_comparisons = []

        if len(matching_batches) == 1:
            batch_id = matching_batches[0]["batch_id"]

            kpis = fetch_kpis(connection, batch_id)
            duplicates = fetch_duplication_metrics(
                connection,
                batch_id,
            )

            if len(kpis) == 1 and len(duplicates) == 1:
                actual = {
                    **kpis[0],
                    **duplicates[0],
                }
                baseline_comparisons = compare_metrics(
                    actual,
                    PHASE1_BASELINE,
                )

    report = build_report(
        completed_batches,
        sql_checks,
        baseline_comparisons,
        source_filename,
        source_sha256,
    )

    write_report(report_path, report)

    print("RIDE360 | WAREHOUSE VALIDATION")
    print("-" * 48)
    print(f"Completed batches: {report['completed_batches']}")
    print(f"SQL quality passed: {report['sql_quality_passed']}")
    print(
        "Phase 1 baseline passed: "
        f"{report['phase1_baseline_passed']}"
    )
    print(f"Overall status: {report['status']}")
    print(f"Report: {report_path}")

    for comparison in baseline_comparisons:
        if not comparison["passed"]:
            print(
                "MISMATCH: "
                f"{comparison['metric']} "
                f"expected={comparison['expected']} "
                f"actual={comparison['actual']}"
            )

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Validate RIDE360 PostgreSQL warehouse"
    )

    parser.add_argument(
        "--env-file",
        type=Path,
        default=DEFAULT_ENV,
    )

    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT,
    )

    args = parser.parse_args()

    report = run_validation(
        env_path=args.env_file,
        source_path=args.source,
        report_path=args.report,
    )

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
