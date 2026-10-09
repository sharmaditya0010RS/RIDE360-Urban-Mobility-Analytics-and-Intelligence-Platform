
-- ============================================================
-- RIDE360 | PHASE 3.4
-- OPERATIONAL ANALYTICS
-- File: sql/operational_analytics.sql
-- ============================================================

BEGIN;

-- 1. Cancellation performance by month and actor.

CREATE OR REPLACE VIEW
    ride360_analytics.monthly_cancellation_intelligence
AS
SELECT
    batch_id,
    booking_month_start,
    COUNT(*)::BIGINT AS total_bookings,

    COUNT(*) FILTER (
        WHERE is_cancelled_by_customer
    )::BIGINT AS customer_cancellations,

    COUNT(*) FILTER (
        WHERE is_cancelled_by_driver
    )::BIGINT AS driver_cancellations,

    COUNT(*) FILTER (
        WHERE is_cancelled
    )::BIGINT AS total_cancellations,

    ROUND(
        100.0 * COUNT(*) FILTER (WHERE is_cancelled)
        / NULLIF(COUNT(*), 0),
        2
    ) AS cancellation_rate_pct,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE is_cancelled_by_customer
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS customer_cancellation_rate_pct,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE is_cancelled_by_driver
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS driver_cancellation_rate_pct

FROM ride360_staging.booking_records_temporal
WHERE booking_month_start IS NOT NULL
GROUP BY batch_id, booking_month_start;


-- 2. Hourly cancellation and no-driver risk.

CREATE OR REPLACE VIEW
    ride360_analytics.hourly_service_risk
AS
SELECT
    batch_id,
    booking_hour,

    COUNT(*)::BIGINT AS total_bookings,

    COUNT(*) FILTER (
        WHERE is_cancelled_by_customer
    )::BIGINT AS customer_cancellations,

    COUNT(*) FILTER (
        WHERE is_cancelled_by_driver
    )::BIGINT AS driver_cancellations,

    COUNT(*) FILTER (
        WHERE is_no_driver_found
    )::BIGINT AS no_driver_found_bookings,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE is_cancelled
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS cancellation_rate_pct,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE is_no_driver_found
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS no_driver_found_rate_pct

FROM ride360_staging.booking_records_temporal
WHERE booking_hour IS NOT NULL
GROUP BY batch_id, booking_hour;


-- 3. Vehicle performance by month.
-- Read vehicle type from the original parsed source payload.

CREATE OR REPLACE VIEW
    ride360_analytics.monthly_vehicle_intelligence
AS
SELECT
    t.batch_id,
    t.booking_month_start,

    COALESCE(
        NULLIF(BTRIM(r.source_payload ->> 'Vehicle Type'), ''),
        'Unknown'
    ) AS vehicle_type,

    COUNT(*)::BIGINT AS total_bookings,

    COUNT(*) FILTER (
        WHERE t.is_completed
    )::BIGINT AS completed_bookings,

    COUNT(*) FILTER (
        WHERE t.is_cancelled
    )::BIGINT AS cancelled_bookings,

    COUNT(*) FILTER (
        WHERE t.is_no_driver_found
    )::BIGINT AS no_driver_found_bookings,

    ROUND(
        100.0 * COUNT(*) FILTER (WHERE t.is_completed)
        / NULLIF(COUNT(*), 0),
        2
    ) AS completion_rate_pct,

    ROUND(
        100.0 * COUNT(*) FILTER (WHERE t.is_cancelled)
        / NULLIF(COUNT(*), 0),
        2
    ) AS cancellation_rate_pct,

    COALESCE(
        SUM(t.completed_booking_value),
        0
    ) AS completed_booking_value_total

FROM ride360_staging.booking_records_temporal AS t

INNER JOIN ride360_raw.booking_records AS r
    ON r.batch_id = t.batch_id
    AND r.raw_record_id = t.raw_record_id

WHERE t.booking_month_start IS NOT NULL

GROUP BY
    t.batch_id,
    t.booking_month_start,
    COALESCE(
        NULLIF(BTRIM(r.source_payload ->> 'Vehicle Type'), ''),
        'Unknown'
    );


-- 4. Cancellation reasons by actor.
-- Empty reason strings are explicitly classified as Unspecified.

CREATE OR REPLACE VIEW
    ride360_analytics.cancellation_reason_intelligence
AS
WITH cancellations AS (
    SELECT
        t.batch_id,
        t.booking_month_start,

        CASE
            WHEN t.is_cancelled_by_customer
                THEN 'Customer'
            WHEN t.is_cancelled_by_driver
                THEN 'Driver'
        END AS cancellation_actor,

        CASE
            WHEN t.is_cancelled_by_customer
            THEN r.source_payload
                ->> 'Reason for cancelling by Customer'

            WHEN t.is_cancelled_by_driver
            THEN r.source_payload
                ->> 'Driver Cancellation Reason'
        END AS reason_text

    FROM ride360_staging.booking_records_temporal AS t

    INNER JOIN ride360_raw.booking_records AS r
        ON r.batch_id = t.batch_id
        AND r.raw_record_id = t.raw_record_id

    WHERE t.is_cancelled
)

SELECT
    batch_id,
    booking_month_start,
    cancellation_actor,

    COALESCE(
        NULLIF(BTRIM(reason_text), ''),
        'Unspecified'
    ) AS cancellation_reason,

    COUNT(*)::BIGINT AS cancellation_records

FROM cancellations

GROUP BY
    batch_id,
    booking_month_start,
    cancellation_actor,
    COALESCE(
        NULLIF(BTRIM(reason_text), ''),
        'Unspecified'
    );


COMMENT ON VIEW
    ride360_analytics.monthly_cancellation_intelligence IS
    'Monthly customer and driver cancellation counts and rates.';

COMMENT ON VIEW
    ride360_analytics.hourly_service_risk IS
    'Hourly cancellation and no-driver-found operational metrics.';

COMMENT ON VIEW
    ride360_analytics.monthly_vehicle_intelligence IS
    'Monthly vehicle-level booking performance.';

COMMENT ON VIEW
    ride360_analytics.cancellation_reason_intelligence IS
    'Monthly cancellation reasons by responsible actor.';

COMMIT;
