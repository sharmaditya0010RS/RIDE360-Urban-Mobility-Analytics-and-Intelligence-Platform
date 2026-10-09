
-- ============================================================
-- RIDE360 | PHASE 3.3
-- BOOKING DEMAND & TEMPORAL ANALYTICS
-- File: sql/demand_analytics.sql
-- PostgreSQL 16+
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- 1. Daily booking trends
-- Grain: batch_id + booking_date
-- ------------------------------------------------------------

CREATE OR REPLACE VIEW
    ride360_analytics.daily_booking_trends
AS
SELECT
    batch_id,
    booking_date,

    COUNT(*)::BIGINT AS total_bookings,

    COUNT(*) FILTER (
        WHERE is_completed
    )::BIGINT AS completed_bookings,

    COUNT(*) FILTER (
        WHERE is_cancelled
    )::BIGINT AS cancelled_bookings,

    COUNT(*) FILTER (
        WHERE is_no_driver_found
    )::BIGINT AS no_driver_found_bookings,

    ROUND(
        100.0 * COUNT(*) FILTER (WHERE is_completed)
        / NULLIF(COUNT(*), 0),
        2
    ) AS completion_rate_pct,

    ROUND(
        100.0 * COUNT(*) FILTER (WHERE is_cancelled)
        / NULLIF(COUNT(*), 0),
        2
    ) AS cancellation_rate_pct,

    COALESCE(
        SUM(completed_booking_value),
        0
    ) AS completed_booking_value_total

FROM ride360_staging.booking_records_temporal
WHERE booking_date IS NOT NULL
GROUP BY batch_id, booking_date;


-- ------------------------------------------------------------
-- 2. Monthly booking trends
-- Grain: batch_id + month
-- ------------------------------------------------------------

CREATE OR REPLACE VIEW
    ride360_analytics.monthly_booking_trends
AS
SELECT
    batch_id,
    booking_month_start,
    booking_year,
    booking_month,

    COUNT(*)::BIGINT AS total_bookings,

    COUNT(*) FILTER (
        WHERE is_completed
    )::BIGINT AS completed_bookings,

    COUNT(*) FILTER (
        WHERE is_cancelled
    )::BIGINT AS cancelled_bookings,

    COUNT(*) FILTER (
        WHERE is_no_driver_found
    )::BIGINT AS no_driver_found_bookings,

    ROUND(
        100.0 * COUNT(*) FILTER (WHERE is_completed)
        / NULLIF(COUNT(*), 0),
        2
    ) AS completion_rate_pct,

    ROUND(
        100.0 * COUNT(*) FILTER (WHERE is_cancelled)
        / NULLIF(COUNT(*), 0),
        2
    ) AS cancellation_rate_pct,

    COALESCE(
        SUM(completed_booking_value),
        0
    ) AS completed_booking_value_total

FROM ride360_staging.booking_records_temporal
WHERE booking_month_start IS NOT NULL
GROUP BY
    batch_id,
    booking_month_start,
    booking_year,
    booking_month;


-- ------------------------------------------------------------
-- 3. Weekday booking demand
-- Grain: batch_id + ISO weekday
-- Monday = 1, Sunday = 7
-- ------------------------------------------------------------

CREATE OR REPLACE VIEW
    ride360_analytics.weekday_booking_demand
AS
SELECT
    batch_id,
    booking_iso_weekday,

    CASE booking_iso_weekday
        WHEN 1 THEN 'Monday'
        WHEN 2 THEN 'Tuesday'
        WHEN 3 THEN 'Wednesday'
        WHEN 4 THEN 'Thursday'
        WHEN 5 THEN 'Friday'
        WHEN 6 THEN 'Saturday'
        WHEN 7 THEN 'Sunday'
    END AS weekday_name,

    COUNT(*)::BIGINT AS total_bookings,

    COUNT(*) FILTER (
        WHERE is_completed
    )::BIGINT AS completed_bookings,

    COUNT(*) FILTER (
        WHERE is_cancelled
    )::BIGINT AS cancelled_bookings,

    ROUND(
        100.0 * COUNT(*) FILTER (WHERE is_completed)
        / NULLIF(COUNT(*), 0),
        2
    ) AS completion_rate_pct,

    COALESCE(
        SUM(completed_booking_value),
        0
    ) AS completed_booking_value_total

FROM ride360_staging.booking_records_temporal
WHERE booking_iso_weekday IS NOT NULL
GROUP BY batch_id, booking_iso_weekday;


-- ------------------------------------------------------------
-- 4. Hourly booking demand
-- Grain: batch_id + hour (0 to 23)
-- ------------------------------------------------------------

CREATE OR REPLACE VIEW
    ride360_analytics.hourly_booking_demand
AS
SELECT
    batch_id,
    booking_hour,

    COUNT(*)::BIGINT AS total_bookings,

    COUNT(*) FILTER (
        WHERE is_completed
    )::BIGINT AS completed_bookings,

    COUNT(*) FILTER (
        WHERE is_cancelled
    )::BIGINT AS cancelled_bookings,

    COUNT(*) FILTER (
        WHERE is_no_driver_found
    )::BIGINT AS no_driver_found_bookings,

    ROUND(
        100.0 * COUNT(*) FILTER (WHERE is_completed)
        / NULLIF(COUNT(*), 0),
        2
    ) AS completion_rate_pct,

    ROUND(
        100.0 * COUNT(*) FILTER (WHERE is_cancelled)
        / NULLIF(COUNT(*), 0),
        2
    ) AS cancellation_rate_pct,

    COALESCE(
        SUM(completed_booking_value),
        0
    ) AS completed_booking_value_total

FROM ride360_staging.booking_records_temporal
WHERE booking_hour IS NOT NULL
GROUP BY batch_id, booking_hour;


-- ------------------------------------------------------------
-- 5. Daypart booking demand
-- Morning:   05:00-11:59
-- Afternoon: 12:00-16:59
-- Evening:   17:00-20:59
-- Night:     21:00-04:59
-- ------------------------------------------------------------

CREATE OR REPLACE VIEW
    ride360_analytics.daypart_booking_demand
AS
SELECT
    batch_id,
    booking_daypart,

    CASE booking_daypart
        WHEN 'Morning' THEN 1
        WHEN 'Afternoon' THEN 2
        WHEN 'Evening' THEN 3
        WHEN 'Night' THEN 4
    END AS daypart_sort_order,

    COUNT(*)::BIGINT AS total_bookings,

    COUNT(*) FILTER (
        WHERE is_completed
    )::BIGINT AS completed_bookings,

    COUNT(*) FILTER (
        WHERE is_cancelled
    )::BIGINT AS cancelled_bookings,

    COUNT(*) FILTER (
        WHERE is_no_driver_found
    )::BIGINT AS no_driver_found_bookings,

    ROUND(
        100.0 * COUNT(*) FILTER (WHERE is_completed)
        / NULLIF(COUNT(*), 0),
        2
    ) AS completion_rate_pct,

    COALESCE(
        SUM(completed_booking_value),
        0
    ) AS completed_booking_value_total

FROM ride360_staging.booking_records_temporal
WHERE booking_daypart IS NOT NULL
GROUP BY batch_id, booking_daypart;


-- ------------------------------------------------------------
-- 6. Weekday x hour demand heatmap
-- Grain: batch_id + ISO weekday + hour
-- ------------------------------------------------------------

CREATE OR REPLACE VIEW
    ride360_analytics.weekday_hour_heatmap
AS
SELECT
    batch_id,
    booking_iso_weekday,
    booking_hour,

    COUNT(*)::BIGINT AS total_bookings,

    COUNT(*) FILTER (
        WHERE is_completed
    )::BIGINT AS completed_bookings,

    COUNT(*) FILTER (
        WHERE is_cancelled
    )::BIGINT AS cancelled_bookings,

    COUNT(*) FILTER (
        WHERE is_no_driver_found
    )::BIGINT AS no_driver_found_bookings

FROM ride360_staging.booking_records_temporal
WHERE
    booking_iso_weekday IS NOT NULL
    AND booking_hour IS NOT NULL
GROUP BY
    batch_id,
    booking_iso_weekday,
    booking_hour;


COMMENT ON VIEW
    ride360_analytics.daily_booking_trends IS
    'Daily booking counts, status rates and completed booking value.';

COMMENT ON VIEW
    ride360_analytics.monthly_booking_trends IS
    'Monthly booking counts, status rates and completed booking value.';

COMMENT ON VIEW
    ride360_analytics.weekday_booking_demand IS
    'Booking demand aggregated by ISO weekday.';

COMMENT ON VIEW
    ride360_analytics.hourly_booking_demand IS
    'Booking demand aggregated by 24-hour clock hour.';

COMMENT ON VIEW
    ride360_analytics.daypart_booking_demand IS
    'Booking demand by defined morning, afternoon, evening and night periods.';

COMMENT ON VIEW
    ride360_analytics.weekday_hour_heatmap IS
    'Booking demand matrix by weekday and hour.';

COMMIT;
