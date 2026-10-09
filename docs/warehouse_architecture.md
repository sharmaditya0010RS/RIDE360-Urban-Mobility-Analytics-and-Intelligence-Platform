
# RIDE360 — PostgreSQL Warehouse Architecture

## 1. Overview

RIDE360 is an end-to-end taxi booking analytics engineering project.

Phase 2 implements a PostgreSQL 16 analytical warehouse that transforms
the source booking CSV into reusable SQL analytics while preserving the
original source-record grain.

The warehouse supports:

- Source ingestion and audit tracking
- Idempotent CSV loading
- Source field preservation
- Typed staging transformations
- Booking status classification
- Duplicate Booking ID investigation
- Executive and operational analytical marts
- Cross-layer reconciliation
- Automated Python validation
- Regression and integration tests

## 2. Source Dataset

Source file:

`data/raw/rideBookings.csv`

Verified source properties:

| Property | Value |
|---|---:|
| Source records | 150,000 |
| Source columns | 21 |
| Distinct Booking IDs | 148,767 |
| Repeated Booking ID groups | 1,224 |
| Records in repeated groups | 2,457 |
| Extra Booking ID occurrences | 1,233 |

Booking ID is not a reliable unique record identifier.

The warehouse therefore uses a surrogate primary key called
`raw_record_id`.

No source records are automatically deduplicated.

## 3. Architecture

```text
CSV Source
data/raw/rideBookings.csv
          |
          v
Python Ingestion
warehouse_pipeline.py
          |
          +--------------------------+
          |                          |
          v                          v
ride360_raw                 ride360_audit
booking_records             ingestion_batches
          |                          |
          v                          |
ride360_staging                       |
normalized -> typed -> classified    |
          |                          |
          v                          |
ride360_analytics                     |
analytical marts                     |
          |                          |
          +-------------+------------+
                        |
                        v
              Warehouse Quality Checks
                        |
                        v
              warehouse_validation.py
                        |
                        v
               JSON Validation Report
```

## 4. Database Schemas

### ride360_raw

Stores parsed original CSV fields.

Main table:

`ride360_raw.booking_records`

Grain:

One row per original CSV record.

Primary key:

`raw_record_id`

Other important columns:

- `batch_id`
- `source_row_number`
- `booking_id_raw`
- `booking_status_raw`
- `source_payload`
- `ingested_at`

`source_payload` is JSONB and preserves the parsed source field values.

JSONB is not a byte-for-byte archival copy of the CSV. The original CSV
file must be retained separately if byte-level reproducibility is needed.

### ride360_audit

Tracks source ingestion and quality checks.

Objects:

- `ingestion_batches`
- `batch_reconciliation`
- `warehouse_quality_checks`
- `warehouse_quality_summary`

### ride360_staging

Normalizes and prepares records without deleting source rows.

Objects:

- `booking_records_normalized`
- `booking_records_typed`
- `booking_records_classified`
- `booking_id_occurrences`
- `repeated_booking_ids`
- `booking_quality_flags`
- `batch_reconciliation`

Date and time remain source text until their formats have been
explicitly validated.

Numeric conversions use guarded casts.

### ride360_analytics

Provides reusable analytical views.

Objects:

- `executive_kpis`
- `booking_status_summary`
- `vehicle_performance`
- `cancellation_reasons`
- `payment_method_summary`
- `pickup_location_performance`
- `route_performance`
- `data_quality_summary`
- `booking_id_duplication_summary`

## 5. Ingestion Design

The Python ingestion module is:

`src/ride360/warehouse_pipeline.py`

### Ingestion process

1. Verify source file exists.
2. Validate the expected 21 CSV headers.
3. Validate source records.
4. Calculate the SHA-256 fingerprint.
5. Connect to PostgreSQL.
6. Acquire a transaction-scoped advisory lock.
7. Check for an existing source fingerprint.
8. Create an ingestion batch if the source is new.
9. Load all CSV records with PostgreSQL COPY.
10. Recalculate source SHA-256.
11. Mark the batch completed.
12. Reconcile loaded and actual database counts.
13. Commit the transaction.
14. Write an ingestion manifest.

### Idempotency

The SHA-256 source fingerprint has a unique database constraint.

Re-running the same source does not create a second batch.

Expected second-run result:

`New batch: False`

### Atomicity

Ingestion uses a PostgreSQL transaction.

If an exception occurs before commit, the database transaction rolls
back.

The JSON ingestion manifest is generated after successful database
reconciliation.

## 6. Analytical KPI Definitions

| KPI | Definition |
|---|---|
| Total booking records | Count of source booking records |
| Completed bookings | Booking Status = Completed |
| Cancelled bookings | Customer + driver cancellations |
| Completion rate | Completed / total records |
| Cancellation rate | Cancelled / total records |
| No driver found rate | No Driver Found / total records |
| Distinct Booking IDs | Count of distinct non-null IDs |
| Completed booking value | Sum of Booking Value for completed records |

All rates use record counts rather than distinct Booking IDs.

Completed booking value is a provisional booking amount.

It is not verified recognized revenue.

The dataset currency and distance units remain unverified.

## 7. Verified Phase 1 Baseline

| Metric | Value |
|---|---:|
| Total booking records | 150,000 |
| Completed | 93,000 |
| Cancelled by Customer | 10,500 |
| Cancelled by Driver | 27,000 |
| Total cancellations | 37,500 |
| Incomplete | 9,000 |
| No Driver Found | 10,500 |
| Completion rate | 62.00% |
| Cancellation rate | 25.00% |
| Completed booking value | 47,260,574 |
| Distinct Booking IDs | 148,767 |

These values are verified for the original RIDE360 source dataset.

They should not be applied as fixed expectations to future datasets.

## 8. Quality Framework

SQL quality checks reconcile:

- Source and raw record counts
- Raw and staging record counts
- Staging and analytical record counts
- Completed bookings
- Cancelled bookings
- Customer cancellations
- Driver cancellations
- Incomplete bookings
- No Driver Found records
- Unknown booking statuses
- Completed booking value
- Distinct Booking IDs
- Status distribution totals
- Vehicle distribution totals
- Payment method distribution totals
- Pickup location distribution totals
- Route distribution totals
- Cancellation reason totals
- Booking status partition completeness
- Duplicate Booking ID count identity

The validation runner also compares the current source fingerprint
against the completed ingestion batch and verifies the Phase 1
baseline for the original dataset.

Validation output:

`reports/generated/warehouse/validation_report.json`

A failed validation returns a nonzero process exit code.

## 9. Execution Order

Run commands from the RIDE360 project root.

### Start PostgreSQL

```powershell
docker compose --env-file .env -f infra/compose.yaml up -d
```

### Apply warehouse schema

```powershell
Get-Content sql/warehouse_schema.sql -Raw |
    docker exec -i ride360_postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

### Apply staging transformations

```powershell
Get-Content sql/staging_transformations.sql -Raw |
    docker exec -i ride360_postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

### Apply analytical marts

```powershell
Get-Content sql/analytical_marts.sql -Raw |
    docker exec -i ride360_postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

### Apply warehouse quality checks

```powershell
Get-Content sql/warehouse_quality_checks.sql -Raw |
    docker exec -i ride360_postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

### Run raw ingestion

```powershell
python -m ride360.warehouse_pipeline
```

### Run warehouse validation

```powershell
python -m ride360.warehouse_validation
```

### Run tests

```powershell
python -m pytest -q
```

### Run linting

```powershell
python -m ruff check .
```

## 10. Reconciliation Query

```sql
SELECT
    batch_id,
    total_checks,
    passed_checks,
    failed_checks,
    all_checks_passed
FROM ride360_audit.warehouse_quality_summary
ORDER BY batch_id;
```

Any failed check can be inspected using:

```sql
SELECT *
FROM ride360_audit.warehouse_quality_checks
WHERE NOT passed
ORDER BY batch_id, check_name;
```

## 11. Known Limitations

- Source Booking IDs are not guaranteed unique.
- JSONB preserves parsed field values, not original CSV bytes.
- Date and time fields are not yet converted into validated timestamps.
- Some numerical source values may be missing or invalid.
- Monetary currency is not independently confirmed.
- Distance units are not independently confirmed.
- Completed booking value is not recognized revenue.
- Source-specific Phase 1 baseline checks must be updated for new
  datasets.
- SQL views calculate on demand; large-scale production deployment
  may require materialization, incremental refresh and indexing.
- A completed-batch registry is not a replacement for database backups.

## 12. Project Structure

```text
RIDE360/
├── data/
│   └── raw/
│       └── rideBookings.csv
├── infra/
│   └── compose.yaml
├── sql/
│   ├── warehouse_schema.sql
│   ├── staging_transformations.sql
│   ├── analytical_marts.sql
│   └── warehouse_quality_checks.sql
├── src/
│   └── ride360/
│       ├── warehouse_pipeline.py
│       └── warehouse_validation.py
├── tests/
│   └── test_warehouse_pipeline.py
├── docs/
│   └── warehouse_architecture.md
└── reports/
    └── generated/
        └── warehouse/
            ├── ingestion_manifest.json
            └── validation_report.json
```

## 13. Completion Criteria

Phase 2 can be marked complete when:

- PostgreSQL is healthy.
- Warehouse schema exists.
- All 150,000 source records are loaded.
- A repeated ingestion does not duplicate records.
- Staging and analytical marts reconcile.
- Warehouse quality checks pass.
- Phase 1 baseline comparison passes.
- Dedicated tests and full regression tests pass.
- Ruff passes.
- Documentation is committed to Git.

## 14. Future Enhancements

Possible future improvements include:

- Validated date/time dimensions
- Materialized analytical marts
- Incremental ingestion
- dbt-based transformations
- Automated CI database provisioning
- Database migration management
- Power BI semantic model
- Dashboard refresh automation
- Additional anomaly detection and monitoring
```
