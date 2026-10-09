
-- ============================================================
-- RIDE360 | STAGING TRANSFORMATIONS
-- ============================================================
-- File: sql/staging_transformations.sql
-- PostgreSQL: 16+
-- Phase: 2.4
--
-- PURPOSE
-- 1. Preserve the source-record grain.
-- 2. Normalize whitespace and empty strings.
-- 3. Safely parse numeric fields.
-- 4. Preserve unparseable source values.
-- 5. Classify booking statuses.
-- 6. Identify repeated Booking IDs.
-- 7. Expose data-quality flags.
--
-- DESIGN
-- Staging is implemented as reusable SQL views.
-- Raw data is never modified by these transformations.
-- ============================================================

BEGIN;


-- ============================================================
-- 01. NORMALIZED SOURCE RECORDS
-- ============================================================

CREATE OR REPLACE VIEW
    ride360_staging.booking_records_normalized
AS
SELECT
    r.raw_record_id,
    r.batch_id,
    r.source_row_number,
    r.ingested_at,

    NULLIF(
        BTRIM(r.source_payload ->> 'Date'),
        ''
    ) AS booking_date_text,

    NULLIF(
        BTRIM(r.source_payload ->> 'Time'),
        ''
    ) AS booking_time_text,

    NULLIF(
        BTRIM(r.source_payload ->> 'Booking ID'),
        ''
    ) AS booking_id,

    NULLIF(
        BTRIM(r.source_payload ->> 'Booking Status'),
        ''
    ) AS booking_status,

    NULLIF(
        BTRIM(r.source_payload ->> 'Customer ID'),
        ''
    ) AS customer_id,

    NULLIF(
        BTRIM(r.source_payload ->> 'Vehicle Type'),
        ''
    ) AS vehicle_type,

    NULLIF(
        BTRIM(r.source_payload ->> 'Pickup Location'),
        ''
    ) AS pickup_location,

    NULLIF(
        BTRIM(r.source_payload ->> 'Drop Location'),
        ''
    ) AS drop_location,

    NULLIF(
        BTRIM(r.source_payload ->> 'Avg VTAT'),
        ''
    ) AS avg_vtat_text,

    NULLIF(
        BTRIM(r.source_payload ->> 'Avg CTAT'),
        ''
    ) AS avg_ctat_text,

    NULLIF(
        BTRIM(
            r.source_payload ->> 'Cancelled Rides by Customer'
        ),
        ''
    ) AS cancelled_by_customer_text,

    NULLIF(
        BTRIM(
            r.source_payload ->> 'Reason for cancelling by Customer'
        ),
        ''
    ) AS customer_cancellation_reason,

    NULLIF(
        BTRIM(
            r.source_payload ->> 'Cancelled Rides by Driver'
        ),
        ''
    ) AS cancelled_by_driver_text,

    NULLIF(
        BTRIM(
            r.source_payload ->> 'Driver Cancellation Reason'
        ),
        ''
    ) AS driver_cancellation_reason,

    NULLIF(
        BTRIM(r.source_payload ->> 'Incomplete Rides'),
        ''
    ) AS incomplete_rides_text,

    NULLIF(
        BTRIM(r.source_payload ->> 'Incomplete Rides Reason'),
        ''
    ) AS incomplete_rides_reason,

    NULLIF(
        BTRIM(r.source_payload ->> 'Booking Value'),
        ''
    ) AS booking_value_text,

    NULLIF(
        BTRIM(r.source_payload ->> 'Ride Distance'),
        ''
    ) AS ride_distance_text,

    NULLIF(
        BTRIM(r.source_payload ->> 'Driver Ratings'),
        ''
    ) AS driver_rating_text,

    NULLIF(
        BTRIM(r.source_payload ->> 'Customer Rating'),
        ''
    ) AS customer_rating_text,

    NULLIF(
        BTRIM(r.source_payload ->> 'Payment Method'),
        ''
    ) AS payment_method,

    r.source_payload

FROM ride360_raw.booking_records AS r

INNER JOIN ride360_audit.ingestion_batches AS b
    ON b.batch_id = r.batch_id

WHERE b.batch_status = 'COMPLETED';


-- ============================================================
-- 02. TYPED BOOKING RECORDS
-- ============================================================
-- Numeric casts are guarded with regular expressions.
-- Invalid values remain NULL in typed columns and retain
-- their original text in the normalized view.
--
-- Date and time are intentionally kept as source text
-- until their formats have been explicitly validated.
-- ============================================================

CREATE OR REPLACE VIEW
    ride360_staging.booking_records_typed
AS
SELECT
    n.*,

    CASE
        WHEN n.avg_vtat_text ~
            '^[+-]?[0-9]+(\.[0-9]+)?$'
        THEN
            CASE
                WHEN LENGTH(n.avg_vtat_text) <= 30
                THEN n.avg_vtat_text::NUMERIC
            END
    END AS avg_vtat,

    CASE
        WHEN n.avg_ctat_text ~
            '^[+-]?[0-9]+(\.[0-9]+)?$'
        THEN
            CASE
                WHEN LENGTH(n.avg_ctat_text) <= 30
                THEN n.avg_ctat_text::NUMERIC
            END
    END AS avg_ctat,

    CASE
        WHEN n.booking_value_text ~
            '^[+-]?[0-9]+(\.[0-9]+)?$'
        THEN
            CASE
                WHEN LENGTH(n.booking_value_text) <= 30
                THEN n.booking_value_text::NUMERIC
            END
    END AS booking_value,

    CASE
        WHEN n.ride_distance_text ~
            '^[+-]?[0-9]+(\.[0-9]+)?$'
        THEN
            CASE
                WHEN LENGTH(n.ride_distance_text) <= 30
                THEN n.ride_distance_text::NUMERIC
            END
    END AS ride_distance,

    CASE
        WHEN n.driver_rating_text ~
            '^[+-]?[0-9]+(\.[0-9]+)?$'
        THEN
            CASE
                WHEN LENGTH(n.driver_rating_text) <= 30
                THEN n.driver_rating_text::NUMERIC
            END
    END AS driver_rating,

    CASE
        WHEN n.customer_rating_text ~
            '^[+-]?[0-9]+(\.[0-9]+)?$'
        THEN
            CASE
                WHEN LENGTH(n.customer_rating_text) <= 30
                THEN n.customer_rating_text::NUMERIC
            END
    END AS customer_rating

FROM ride360_staging.booking_records_normalized AS n;


-- ============================================================
-- 03. BOOKING STATUS CLASSIFICATION
-- ============================================================
-- Booking status is the authoritative classification.
-- Raw cancellation indicator fields are preserved
-- separately for later consistency checks.
-- ============================================================

CREATE OR REPLACE VIEW
    ride360_staging.booking_records_classified
AS
SELECT
    t.*,

    CASE
        WHEN t.booking_status = 'Completed'
        THEN TRUE
        ELSE FALSE
    END AS is_completed,

    CASE
        WHEN t.booking_status = 'Cancelled by Customer'
        THEN TRUE
        ELSE FALSE
    END AS is_cancelled_by_customer,

    CASE
        WHEN t.booking_status = 'Cancelled by Driver'
        THEN TRUE
        ELSE FALSE
    END AS is_cancelled_by_driver,

    CASE
        WHEN t.booking_status IN (
            'Cancelled by Customer',
            'Cancelled by Driver'
        )
        THEN TRUE
        ELSE FALSE
    END AS is_cancelled,

    CASE
        WHEN t.booking_status = 'Incomplete'
        THEN TRUE
        ELSE FALSE
    END AS is_incomplete,

    CASE
        WHEN t.booking_status = 'No Driver Found'
        THEN TRUE
        ELSE FALSE
    END AS is_no_driver_found,

    CASE
        WHEN t.booking_status IN (
            'Completed',
            'Cancelled by Customer',
            'Cancelled by Driver',
            'Incomplete',
            'No Driver Found'
        )
        THEN TRUE
        ELSE FALSE
    END AS has_known_booking_status,

    CASE
        WHEN t.booking_status = 'Completed'
        THEN t.booking_value
        ELSE NULL
    END AS completed_booking_value

FROM ride360_staging.booking_records_typed AS t;


-- ============================================================
-- 04. DUPLICATE BOOKING ID INVESTIGATION
-- ============================================================
-- Repeated Booking IDs are flagged, never removed.
-- Counts are scoped to each ingestion batch.
-- ============================================================

CREATE OR REPLACE VIEW
    ride360_staging.booking_id_occurrences
AS
SELECT
    batch_id,
    booking_id,
    COUNT(*)::BIGINT AS occurrence_count

FROM ride360_staging.booking_records_normalized

WHERE booking_id IS NOT NULL

GROUP BY
    batch_id,
    booking_id;


CREATE OR REPLACE VIEW
    ride360_staging.repeated_booking_ids
AS
SELECT
    batch_id,
    booking_id,
    occurrence_count

FROM ride360_staging.booking_id_occurrences

WHERE occurrence_count > 1;


-- ============================================================
-- 05. DATA QUALITY FLAGS
-- ============================================================

CREATE OR REPLACE VIEW
    ride360_staging.booking_quality_flags
AS
SELECT
    c.raw_record_id,
    c.batch_id,
    c.source_row_number,
    c.booking_id,
    c.booking_status,

    COALESCE(
        o.occurrence_count,
        0
    ) AS booking_id_occurrence_count,

    (
        COALESCE(o.occurrence_count, 0) > 1
    ) AS has_repeated_booking_id,

    (
        c.booking_id IS NULL
    ) AS missing_booking_id,

    (
        NOT c.has_known_booking_status
    ) AS unknown_booking_status,

    (
        c.booking_value_text IS NOT NULL
        AND c.booking_value IS NULL
    ) AS invalid_booking_value,

    (
        c.ride_distance_text IS NOT NULL
        AND c.ride_distance IS NULL
    ) AS invalid_ride_distance,

    (
        c.driver_rating_text IS NOT NULL
        AND c.driver_rating IS NULL
    ) AS invalid_driver_rating,

    (
        c.customer_rating_text IS NOT NULL
        AND c.customer_rating IS NULL
    ) AS invalid_customer_rating,

    (
        c.booking_value IS NOT NULL
        AND c.booking_value < 0
    ) AS negative_booking_value,

    (
        c.ride_distance IS NOT NULL
        AND c.ride_distance < 0
    ) AS negative_ride_distance,

    (
        c.driver_rating IS NOT NULL
        AND (
            c.driver_rating < 0
            OR c.driver_rating > 5
        )
    ) AS driver_rating_out_of_range,

    (
        c.customer_rating IS NOT NULL
        AND (
            c.customer_rating < 0
            OR c.customer_rating > 5
        )
    ) AS customer_rating_out_of_range

FROM ride360_staging.booking_records_classified AS c

LEFT JOIN ride360_staging.booking_id_occurrences AS o
    ON o.batch_id = c.batch_id
    AND o.booking_id = c.booking_id;


-- ============================================================
-- 06. STAGING RECONCILIATION
-- ============================================================

CREATE OR REPLACE VIEW
    ride360_staging.batch_reconciliation
AS
SELECT
    b.batch_id,
    b.source_filename,
    b.source_record_count,

    COUNT(c.raw_record_id)::BIGINT
        AS staging_record_count,

    (
        b.source_record_count
        = COUNT(c.raw_record_id)
    ) AS source_count_matches,

    COUNT(c.raw_record_id)
        FILTER (
            WHERE c.is_completed
        )::BIGINT AS completed_records,

    COUNT(c.raw_record_id)
        FILTER (
            WHERE c.is_cancelled_by_customer
        )::BIGINT AS customer_cancelled_records,

    COUNT(c.raw_record_id)
        FILTER (
            WHERE c.is_cancelled_by_driver
        )::BIGINT AS driver_cancelled_records,

    COUNT(c.raw_record_id)
        FILTER (
            WHERE c.is_incomplete
        )::BIGINT AS incomplete_records,

    COUNT(c.raw_record_id)
        FILTER (
            WHERE c.is_no_driver_found
        )::BIGINT AS no_driver_found_records,

    COUNT(c.raw_record_id)
        FILTER (
            WHERE NOT c.has_known_booking_status
        )::BIGINT AS unknown_status_records,

    SUM(c.completed_booking_value)
        AS completed_booking_value_total

FROM ride360_audit.ingestion_batches AS b

LEFT JOIN ride360_staging.booking_records_classified AS c
    ON c.batch_id = b.batch_id

WHERE b.batch_status = 'COMPLETED'

GROUP BY
    b.batch_id,
    b.source_filename,
    b.source_record_count;


-- ============================================================
-- 07. DOCUMENTATION
-- ============================================================

COMMENT ON VIEW
    ride360_staging.booking_records_normalized IS
    'Whitespace-normalized source fields, one row per CSV record.';


COMMENT ON VIEW
    ride360_staging.booking_records_typed IS
    'Safe numeric conversions while preserving original text.';


COMMENT ON VIEW
    ride360_staging.booking_records_classified IS
    'Booking status flags and provisional completed booking value.';


COMMENT ON VIEW
    ride360_staging.booking_id_occurrences IS
    'Per-batch counts of non-null Booking IDs.';


COMMENT ON VIEW
    ride360_staging.repeated_booking_ids IS
    'Booking IDs appearing more than once in a batch.';


COMMENT ON VIEW
    ride360_staging.booking_quality_flags IS
    'Record-level staging quality and repeated-ID flags.';


COMMENT ON VIEW
    ride360_staging.batch_reconciliation IS
    'Staging counts and status reconciliation per completed batch.';


COMMIT;

-- ============================================================
-- END OF FILE
-- ============================================================
