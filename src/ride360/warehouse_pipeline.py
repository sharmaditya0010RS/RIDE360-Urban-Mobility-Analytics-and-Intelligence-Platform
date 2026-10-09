
"""RIDE360 PostgreSQL raw warehouse ingestion pipeline.

Run:
    python -m ride360.warehouse_pipeline

Properties:
- Preserves all original CSV records.
- Keeps duplicate Booking IDs.
- Uses SHA-256 for idempotent ingestion.
- Loads records in a single database transaction.
- Validates source schema and row counts.
- Reads PostgreSQL credentials from project .env.
"""

import argparse
import csv
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import psycopg
from dotenv import dotenv_values
from psycopg.types.json import Jsonb

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_SOURCE = PROJECT_ROOT / "data" / "raw" / "rideBookings.csv"
DEFAULT_ENV = PROJECT_ROOT / ".env"
DEFAULT_REPORT = (
    PROJECT_ROOT
    / "reports"
    / "generated"
    / "warehouse"
    / "ingestion_manifest.json"
)

EXPECTED_COLUMNS = (
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
)


def calculate_sha256(path: Path) -> str:
    """Calculate SHA-256 without loading the whole file."""
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def read_source(path: Path):
    """Yield validated source records, preserving text values."""
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        if tuple(reader.fieldnames or ()) != EXPECTED_COLUMNS:
            raise ValueError(
                "CSV schema mismatch.\n"
                f"Expected: {EXPECTED_COLUMNS}\n"
                f"Found: {reader.fieldnames}"
            )

        for source_row_number, record in enumerate(
            reader,
            start=2,
        ):
            if None in record:
                raise ValueError(
                    "Extra CSV fields at record "
                    f"{source_row_number}"
                )

            if any(value is None for value in record.values()):
                raise ValueError(
                    "Missing CSV fields at record "
                    f"{source_row_number}"
                )

            yield source_row_number, record


def count_source_records(path: Path) -> int:
    """Validate the full CSV and count its records."""
    return sum(1 for _ in read_source(path))


def get_database_config(env_path: Path) -> dict:
    """Read database credentials without printing secrets."""
    if not env_path.is_file():
        raise FileNotFoundError(
            f"Environment file not found: {env_path}"
        )

    values = dotenv_values(env_path)

    password = values.get("POSTGRES_PASSWORD")

    if not password:
        raise ValueError(
            "POSTGRES_PASSWORD missing from .env"
        )

    return {
        "host": "127.0.0.1",
        "port": 5433,
        "dbname": values.get("POSTGRES_DB") or "ride360",
        "user": values.get("POSTGRES_USER") or "ride360",
        "password": password,
        "connect_timeout": 10,
    }


def ensure_schema_exists(connection) -> None:
    """Check that Step 2.2 was executed."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                to_regclass(
                    'ride360_audit.ingestion_batches'
                ),
                to_regclass(
                    'ride360_raw.booking_records'
                )
            """
        )

        batch_table, raw_table = cursor.fetchone()

        if batch_table is None or raw_table is None:
            raise RuntimeError(
                "Warehouse tables are missing. "
                "Execute sql/warehouse_schema.sql first."
            )


def find_existing_batch(
    connection,
    source_sha256: str,
):
    """Find a previously ingested source fingerprint."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                batch_id,
                source_record_count,
                loaded_record_count,
                batch_status
            FROM ride360_audit.ingestion_batches
            WHERE source_sha256 = %s
            """,
            (source_sha256,),
        )

        return cursor.fetchone()


def verify_batch(
    connection,
    batch_id: int,
    expected_rows: int,
) -> dict:
    """Verify registry and actual raw-table counts."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                source_record_count,
                loaded_record_count,
                actual_raw_record_count,
                loaded_count_matches,
                source_count_matches,
                batch_status
            FROM ride360_audit.batch_reconciliation
            WHERE batch_id = %s
            """,
            (batch_id,),
        )

        row = cursor.fetchone()

        if row is None:
            raise RuntimeError(
                f"Batch {batch_id} reconciliation missing"
            )

        (
            source_count,
            loaded_count,
            actual_count,
            loaded_matches,
            source_matches,
            status,
        ) = row

        passed = (
            source_count == expected_rows
            and loaded_count == expected_rows
            and actual_count == expected_rows
            and loaded_matches
            and source_matches
            and status == "COMPLETED"
        )

        if not passed:
            raise RuntimeError(
                "Warehouse reconciliation failed: "
                f"batch={batch_id}, "
                f"source={source_count}, "
                f"loaded={loaded_count}, "
                f"actual={actual_count}, "
                f"status={status}"
            )

        return {
            "status": "PASS",
            "source_record_count": int(source_count),
            "loaded_record_count": int(loaded_count),
            "actual_raw_record_count": int(actual_count),
        }


def ingest_source(
    connection,
    source: Path,
    source_sha256: str,
    expected_rows: int,
) -> tuple[int, bool]:
    """Ingest source atomically or reuse a completed batch."""
    # A transaction-scoped advisory lock prevents concurrent
    # loaders for this warehouse from racing each other.
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT pg_advisory_xact_lock(%s)",
            (3602026,),
        )

    existing = find_existing_batch(
        connection,
        source_sha256,
    )

    if existing is not None:
        (
            batch_id,
            previous_source_count,
            previous_loaded_count,
            previous_status,
        ) = existing

        if previous_status != "COMPLETED":
            raise RuntimeError(
                "Existing source fingerprint has "
                f"non-completed batch: {previous_status}"
            )

        if (
            previous_source_count != expected_rows
            or previous_loaded_count != expected_rows
        ):
            raise RuntimeError(
                "Existing batch counts do not match source"
            )

        return int(batch_id), False

    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO ride360_audit.ingestion_batches (
                source_filename,
                source_sha256,
                source_record_count,
                loaded_record_count,
                batch_status
            )
            VALUES (%s, %s, %s, 0, 'LOADING')
            RETURNING batch_id
            """,
            (
                source.name,
                source_sha256,
                expected_rows,
            ),
        )

        batch_id = int(cursor.fetchone()[0])

        loaded_rows = 0

        with cursor.copy(
            """
            COPY ride360_raw.booking_records (
                batch_id,
                source_row_number,
                booking_id_raw,
                booking_status_raw,
                source_payload
            )
            FROM STDIN
            """
        ) as copy:
            for source_row_number, record in read_source(
                source
            ):
                copy.write_row(
                    (
                        batch_id,
                        source_row_number,
                        record["Booking ID"],
                        record["Booking Status"],
                        Jsonb(record),
                    )
                )
                loaded_rows += 1

        if loaded_rows != expected_rows:
            raise RuntimeError(
                "CSV changed during ingestion or row "
                f"count mismatch: {loaded_rows} "
                f"!= {expected_rows}"
            )

        # Detect source modification during the load.
        if calculate_sha256(source) != source_sha256:
            raise RuntimeError(
                "Source file changed during ingestion"
            )

        cursor.execute(
            """
            UPDATE ride360_audit.ingestion_batches
            SET
                loaded_record_count = %s,
                batch_status = 'COMPLETED',
                completed_at = NOW()
            WHERE batch_id = %s
            """,
            (loaded_rows, batch_id),
        )

    return batch_id, True


def write_manifest(
    output_path: Path,
    manifest: dict,
) -> None:
    """Write a machine-readable ingestion report."""
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def run_pipeline(
    source: Path = DEFAULT_SOURCE,
    env_path: Path = DEFAULT_ENV,
    report_path: Path = DEFAULT_REPORT,
) -> dict:
    """Run the complete raw-ingestion checkpoint."""
    source = Path(source).resolve()

    if not source.is_file():
        raise FileNotFoundError(
            f"Source CSV not found: {source}"
        )

    print("RIDE360 | POSTGRESQL RAW INGESTION")
    print("-" * 48)

    print("Validating source CSV...")
    expected_rows = count_source_records(source)

    print(f"Source records: {expected_rows:,}")

    source_sha256 = calculate_sha256(source)

    print(f"Source SHA-256: {source_sha256}")

    config = get_database_config(
        Path(env_path)
    )

    # One connection context, one transaction.
    # An exception rolls back the entire ingestion.
    with psycopg.connect(**config) as connection:
        ensure_schema_exists(connection)

        batch_id, new_batch = ingest_source(
            connection,
            source,
            source_sha256,
            expected_rows,
        )

        reconciliation = verify_batch(
            connection,
            batch_id,
            expected_rows,
        )

    manifest = {
        "project": "RIDE360",
        "pipeline": "PostgreSQL Raw Warehouse Ingestion",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "status": "PASS",
        "source_filename": source.name,
        "source_sha256": source_sha256,
        "batch_id": batch_id,
        "new_batch_inserted": new_batch,
        "source_columns": len(EXPECTED_COLUMNS),
        "source_records": expected_rows,
        "reconciliation": reconciliation,
        "policies": {
            "source_modified": False,
            "automatic_deduplication": False,
            "booking_id_as_primary_key": False,
            "raw_record_grain_preserved": True,
        },
    }

    write_manifest(
        Path(report_path),
        manifest,
    )

    print(f"Batch ID: {batch_id}")
    print(f"New batch: {new_batch}")
    print(
        "Database records: "
        f"{reconciliation['actual_raw_record_count']:,}"
    )
    print(
        "Reconciliation: "
        f"{reconciliation['status']}"
    )
    print(f"Manifest: {report_path}")
    print("Overall status: PASS")

    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="RIDE360 raw PostgreSQL ingestion"
    )

    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
    )

    parser.add_argument(
        "--env-file",
        type=Path,
        default=DEFAULT_ENV,
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT,
    )

    args = parser.parse_args()

    run_pipeline(
        source=args.source,
        env_path=args.env_file,
        report_path=args.report,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
