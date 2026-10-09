-- ============================================================
-- RIDE360 | PHASE 3.2
-- VALIDATED TEMPORAL TRANSFORMATIONS
-- File: sql/temporal_transformations.sql
-- PostgreSQL 16+
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- 1. Validate source date and time strings.
--
-- Regex checks format.
-- make_date is called only after numeric range checks.
-- PostgreSQL's make_date still rejects impossible dates, so
-- we validate the day against the month's actual last day
-- before constructing the final date.
-- ------------------------------------------------------------

CREATE OR REPLACE VIEW
    ride360_staging.booking_temporal_validation
AS
WITH source_data AS (
    SELECT
        batch_id,
        raw_record_id,
        source_row_number,
        booking_id,
        booking_status,
        booking_date_text,
        booking_time_text
    FROM ride360_staging.booking_records_normalized
),
format_checks AS (
    SELECT
        *,
        (
            booking_date_text ~
            '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
        ) AS date_format_valid,
        (
            booking_time_text ~
            '^[0-9]{2}:[0-9]{2}:[0-9]{2}$'
        ) AS time_format_valid
    FROM source_data
),
date_parts AS (
    SELECT
        *,
        CASE
            WHEN date_format_valid
            THEN SUBSTRING(booking_date_text, 1, 4)::INTEGER
        END AS date_year,
        CASE
            WHEN date_format_valid
            THEN SUBSTRING(booking_date_text, 6, 2)::INTEGER
        END AS date_month,
        CASE
            WHEN date_format_valid
            THEN SUBSTRING(booking_date_text, 9, 2)::INTEGER
        END AS date_day,
        CASE
            WHEN time_format_valid
            THEN SUBSTRING(booking_time_text, 1, 2)::INTEGER
        END AS time_hour,
        CASE
            WHEN time_format_valid
            THEN SUBSTRING(booking_time_text, 4, 2)::INTEGER
        END AS time_minute,
        CASE
            WHEN time_format_valid
            THEN SUBSTRING(booking_time_text, 7, 2)::INTEGER
        END AS time_second
    FROM format_checks
),
range_checks AS (
    SELECT
        *,
        (
            date_format_valid
            AND date_year BETWEEN 1 AND 9999
            AND date_month BETWEEN 1 AND 12
            AND date_day BETWEEN 1 AND 31
        ) AS date_basic_range_valid,
        (
            time_format_valid
            AND time_hour BETWEEN 0 AND 23
            AND time_minute BETWEEN 0 AND 59
            AND time_second BETWEEN 0 AND 59
        ) AS time_range_valid
    FROM date_parts
),
calendar_checks AS (
    SELECT
        *,
        CASE
            WHEN date_basic_range_valid
            THEN date_day <= EXTRACT(
                DAY FROM (
                    make_date(date_year, date_month, 1)
                    + INTERVAL '1 month'
                    - INTERVAL '1 day'
                )
            )::INTEGER
            ELSE FALSE
        END AS date_calendar_valid
    FROM range_checks
)
SELECT
    batch_id,
    raw_record_id,
    source_row_number,
    booking_id,
    booking_status,
    booking_date_text,
    booking_time_text,

    COALESCE(date_format_valid, FALSE)
        AS date_format_valid,

    COALESCE(date_calendar_valid, FALSE)
        AS date_valid,

    COALESCE(time_format_valid, FALSE)
        AS time_format_valid,

    COALESCE(time_range_valid, FALSE)
        AS time_valid,

    CASE
        WHEN date_calendar_valid
        THEN make_date(date_year, date_month, date_day)
    END AS booking_date,

    CASE
        WHEN time_range_valid
        THEN make_time(
            time_hour,
            time_minute,
            time_second
        )
    END AS booking_time

FROM calendar_checks;


-- ------------------------------------------------------------
-- 2. Enrich classified booking records with validated
--    temporal dimensions.
--
-- One record remains one record.
-- The surrogate raw_record_id is the join key.
-- ------------------------------------------------------------

CREATE OR REPLACE VIEW
    ride360_staging.booking_records_temporal
AS
SELECT
    c.*,

    t.booking_date,
    t.booking_time,

    CASE
        WHEN t.date_valid AND t.time_valid
        THEN t.booking_date + t.booking_time
    END AS booking_timestamp,

    t.date_valid,
    t.time_valid,

    (
        t.date_valid AND t.time_valid
    ) AS temporal_valid,

    CASE
        WHEN t.date_valid
        THEN EXTRACT(YEAR FROM t.booking_date)::INTEGER
    END AS booking_year,

    CASE
        WHEN t.date_valid
        THEN EXTRACT(MONTH FROM t.booking_date)::INTEGER
    END AS booking_month,

    CASE
        WHEN t.date_valid
        THEN EXTRACT(
            QUARTER FROM t.booking_date
        )::INTEGER
    END AS booking_quarter,

    CASE
        WHEN t.date_valid
        THEN EXTRACT(
            ISODOW FROM t.booking_date
        )::INTEGER
    END AS booking_iso_weekday,

    CASE
        WHEN t.time_valid
        THEN EXTRACT(HOUR FROM t.booking_time)::INTEGER
    END AS booking_hour,

    CASE
        WHEN t.date_valid
        THEN DATE_TRUNC(
            'month',
            t.booking_date::TIMESTAMP
        )::DATE
    END AS booking_month_start,

    CASE
        WHEN t.date_valid
        THEN DATE_TRUNC(
            'week',
            t.booking_date::TIMESTAMP
        )::DATE
    END AS booking_week_start,

    CASE
        WHEN t.time_valid
        THEN
            CASE
                WHEN EXTRACT(HOUR FROM t.booking_time)
                    BETWEEN 5 AND 11
                    THEN 'Morning'

                WHEN EXTRACT(HOUR FROM t.booking_time)
                    BETWEEN 12 AND 16
                    THEN 'Afternoon'

                WHEN EXTRACT(HOUR FROM t.booking_time)
                    BETWEEN 17 AND 20
                    THEN 'Evening'

                ELSE 'Night'
            END
    END AS booking_daypart

FROM ride360_staging.booking_records_classified AS c

INNER JOIN ride360_staging.booking_temporal_validation AS t
    ON t.batch_id = c.batch_id
    AND t.raw_record_id = c.raw_record_id;


-- ------------------------------------------------------------
-- 3. Temporal data quality summary.
-- ------------------------------------------------------------

CREATE OR REPLACE VIEW
    ride360_audit.temporal_quality_summary
AS
SELECT
    batch_id,

    COUNT(*)::BIGINT AS total_records,

    COUNT(*) FILTER (
        WHERE date_valid
    )::BIGINT AS valid_date_records,

    COUNT(*) FILTER (
        WHERE NOT date_valid
    )::BIGINT AS invalid_date_records,

    COUNT(*) FILTER (
        WHERE time_valid
    )::BIGINT AS valid_time_records,

    COUNT(*) FILTER (
        WHERE NOT time_valid
    )::BIGINT AS invalid_time_records,

    COUNT(*) FILTER (
        WHERE temporal_valid
    )::BIGINT AS valid_timestamp_records,

    COUNT(*) FILTER (
        WHERE NOT temporal_valid
    )::BIGINT AS invalid_timestamp_records,

    MIN(booking_date) AS earliest_booking_date,
    MAX(booking_date) AS latest_booking_date,

    MIN(booking_timestamp) AS earliest_booking_timestamp,
    MAX(booking_timestamp) AS latest_booking_timestamp

FROM ride360_staging.booking_records_temporal
GROUP BY batch_id;


COMMENT ON VIEW
    ride360_staging.booking_temporal_validation IS
    'Validates source date/time formats, calendar dates and clock ranges.';

COMMENT ON VIEW
    ride360_staging.booking_records_temporal IS
    'Enriches classified bookings with validated temporal dimensions.';

COMMENT ON VIEW
    ride360_audit.temporal_quality_summary IS
    'Summarizes temporal validity and observed booking date ranges.';

COMMIT;