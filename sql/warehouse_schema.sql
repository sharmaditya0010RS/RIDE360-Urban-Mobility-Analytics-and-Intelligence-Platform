
-- ============================================================
-- RIDE360 | POSTGRESQL DATA WAREHOUSE
-- ============================================================
-- File: sql/warehouse_schema.sql
-- PostgreSQL Version: 16+
-- Phase: 2 - Data Warehouse & ETL Engineering
--
-- DESIGN PRINCIPLES
-- 1. One raw record per original CSV row.
-- 2. Booking ID is not a primary key.
-- 3. Duplicate Booking IDs are preserved.
-- 4. Original source values remain in JSONB.
-- 5. SHA-256 enables idempotent ingestion.
-- 6. All data loads are tracked by batch ID.
-- ============================================================

BEGIN;

-- ============================================================
-- 01. WAREHOUSE SCHEMAS
-- ============================================================

CREATE SCHEMA IF NOT EXISTS ride360_raw;

CREATE SCHEMA IF NOT EXISTS ride360_staging;

CREATE SCHEMA IF NOT EXISTS ride360_analytics;

CREATE SCHEMA IF NOT EXISTS ride360_audit;


-- ============================================================
-- 02. INGESTION BATCH REGISTRY
-- ============================================================

CREATE TABLE IF NOT EXISTS ride360_audit.ingestion_batches (

    batch_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    source_filename TEXT NOT NULL,

    source_sha256 CHAR(64) NOT NULL,

    source_record_count BIGINT NOT NULL
        CHECK (source_record_count >= 0),

    loaded_record_count BIGINT NOT NULL DEFAULT 0
        CHECK (loaded_record_count >= 0),

    batch_status TEXT NOT NULL DEFAULT 'LOADING'
        CHECK (
            batch_status IN (
                'LOADING',
                'COMPLETED',
                'FAILED'
            )
        ),

    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    completed_at TIMESTAMPTZ,

    CONSTRAINT uq_ride360_source_sha256
        UNIQUE (source_sha256),

    CONSTRAINT chk_ride360_sha256_format
        CHECK (
            source_sha256 ~ '^[0-9a-f]{64}$'
        ),

    CONSTRAINT chk_ride360_batch_counts
        CHECK (
            loaded_record_count <= source_record_count
        ),

    CONSTRAINT chk_ride360_completed_batch
        CHECK (
            batch_status <> 'COMPLETED'
            OR (
                completed_at IS NOT NULL
                AND loaded_record_count = source_record_count
            )
        )
);


-- ============================================================
-- 03. RAW BOOKING RECORDS
-- ============================================================

CREATE TABLE IF NOT EXISTS ride360_raw.booking_records (

    raw_record_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    batch_id BIGINT NOT NULL,

    source_row_number BIGINT NOT NULL
        CHECK (source_row_number >= 2),

    booking_id_raw TEXT,

    booking_status_raw TEXT,

    source_payload JSONB NOT NULL,

    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_ride360_booking_batch
        FOREIGN KEY (batch_id)
        REFERENCES ride360_audit.ingestion_batches (
            batch_id
        )
        ON DELETE RESTRICT,

    CONSTRAINT uq_ride360_batch_source_row
        UNIQUE (
            batch_id,
            source_row_number
        ),

    CONSTRAINT chk_ride360_payload_object
        CHECK (
            jsonb_typeof(source_payload) = 'object'
        )
);


-- ============================================================
-- 04. PERFORMANCE INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS
    idx_ride360_batch_status
ON ride360_audit.ingestion_batches (
    batch_status
);


CREATE INDEX IF NOT EXISTS
    idx_ride360_raw_batch_id
ON ride360_raw.booking_records (
    batch_id
);


CREATE INDEX IF NOT EXISTS
    idx_ride360_raw_booking_id
ON ride360_raw.booking_records (
    batch_id,
    booking_id_raw
);


CREATE INDEX IF NOT EXISTS
    idx_ride360_raw_booking_status
ON ride360_raw.booking_records (
    batch_id,
    booking_status_raw
);


-- ============================================================
-- 05. BATCH RECONCILIATION VIEW
-- ============================================================

CREATE OR REPLACE VIEW
    ride360_audit.batch_reconciliation
AS

SELECT

    b.batch_id,

    b.source_filename,

    b.source_sha256,

    b.batch_status,

    b.source_record_count,

    b.loaded_record_count,

    COUNT(r.raw_record_id)::BIGINT
        AS actual_raw_record_count,

    (
        b.loaded_record_count
        = COUNT(r.raw_record_id)
    ) AS loaded_count_matches,

    (
        b.source_record_count
        = COUNT(r.raw_record_id)
    ) AS source_count_matches,

    b.started_at,

    b.completed_at

FROM ride360_audit.ingestion_batches AS b

LEFT JOIN ride360_raw.booking_records AS r
    ON r.batch_id = b.batch_id

GROUP BY
    b.batch_id,
    b.source_filename,
    b.source_sha256,
    b.batch_status,
    b.source_record_count,
    b.loaded_record_count,
    b.started_at,
    b.completed_at;


-- ============================================================
-- 06. DATABASE DOCUMENTATION
-- ============================================================

COMMENT ON SCHEMA ride360_raw IS
    'Lossless source-record landing layer for RIDE360.';


COMMENT ON SCHEMA ride360_staging IS
    'Typed and validated transformation layer.';


COMMENT ON SCHEMA ride360_analytics IS
    'Reusable analytical views and data marts.';


COMMENT ON SCHEMA ride360_audit IS
    'Ingestion tracking, quality checks and reconciliation.';


COMMENT ON TABLE ride360_raw.booking_records IS
    'One row per source CSV record; Booking ID may repeat.';


COMMENT ON COLUMN
    ride360_raw.booking_records.raw_record_id IS
    'Surrogate primary key, independent of Booking ID.';


COMMENT ON COLUMN
    ride360_raw.booking_records.source_row_number IS
    'Original CSV line number, starting at line 2.';


COMMENT ON COLUMN
    ride360_raw.booking_records.source_payload IS
    'Original CSV fields represented as a JSONB object.';


COMMENT ON TABLE
    ride360_audit.ingestion_batches IS
    'SHA-256 keyed ingestion registry for idempotent loads.';


-- ============================================================
-- 07. COMMIT TRANSACTION
-- ============================================================

COMMIT;

-- ============================================================
-- END OF FILE
-- ============================================================
