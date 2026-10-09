
-- ============================================================
-- RIDE360 | ANALYTICAL DATA MARTS
-- ============================================================
-- File: sql/analytical_marts.sql
-- PostgreSQL: 16+
-- Phase: 2.5
--
-- DESIGN PRINCIPLES
-- 1. Source-record grain is preserved in staging.
-- 2. Analytical marts aggregate records, not unique IDs.
-- 3. No automatic Booking ID deduplication.
-- 4. Completed booking value is not recognized revenue.
-- 5. Currency and distance units remain unverified.
-- 6. All marts include batch_id for traceability.
-- 7. Percentage metrics use safe division.
-- ============================================================

BEGIN;


-- ============================================================
-- 01. EXECUTIVE KPI MART
-- Grain: One row per ingestion batch
-- ============================================================

CREATE OR REPLACE VIEW
    ride360_analytics.executive_kpis
AS
SELECT
    c.batch_id,

    COUNT(*)::BIGINT AS total_booking_records,

    COUNT(*) FILTER (
        WHERE c.is_completed
    )::BIGINT AS completed_bookings,

    COUNT(*) FILTER (
        WHERE c.is_cancelled
    )::BIGINT AS cancelled_bookings,

    COUNT(*) FILTER (
        WHERE c.is_cancelled_by_customer
    )::BIGINT AS customer_cancelled_bookings,

    COUNT(*) FILTER (
        WHERE c.is_cancelled_by_driver
    )::BIGINT AS driver_cancelled_bookings,

    COUNT(*) FILTER (
        WHERE c.is_incomplete
    )::BIGINT AS incomplete_bookings,

    COUNT(*) FILTER (
        WHERE c.is_no_driver_found
    )::BIGINT AS no_driver_found_bookings,

    COUNT(*) FILTER (
        WHERE NOT c.has_known_booking_status
    )::BIGINT AS unknown_status_bookings,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE c.is_completed
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS completion_rate_pct,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE c.is_cancelled
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS cancellation_rate_pct,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE c.is_no_driver_found
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS no_driver_found_rate_pct,

    COALESCE(
        SUM(c.completed_booking_value),
        0
    ) AS completed_booking_value_total,

    ROUND(
        AVG(c.booking_value) FILTER (
            WHERE c.is_completed
        ),
        2
    ) AS avg_completed_booking_value,

    ROUND(
        AVG(c.ride_distance) FILTER (
            WHERE c.is_completed
        ),
        2
    ) AS avg_completed_ride_distance,

    ROUND(
        AVG(c.driver_rating) FILTER (
            WHERE c.is_completed
        ),
        2
    ) AS avg_completed_driver_rating,

    ROUND(
        AVG(c.customer_rating) FILTER (
            WHERE c.is_completed
        ),
        2
    ) AS avg_completed_customer_rating,

    COUNT(DISTINCT c.booking_id)::BIGINT
        AS distinct_booking_ids

FROM ride360_staging.booking_records_classified AS c

GROUP BY
    c.batch_id;


-- ============================================================
-- 02. BOOKING STATUS DISTRIBUTION
-- Grain: Batch + Booking Status
-- ============================================================

CREATE OR REPLACE VIEW
    ride360_analytics.booking_status_summary
AS
SELECT
    c.batch_id,

    COALESCE(
        c.booking_status,
        'MISSING'
    ) AS booking_status,

    COUNT(*)::BIGINT AS booking_records,

    ROUND(
        100.0 * COUNT(*)
        / NULLIF(
            SUM(COUNT(*)) OVER (
                PARTITION BY c.batch_id
            ),
            0
        ),
        2
    ) AS share_of_batch_pct,

    COALESCE(
        SUM(c.completed_booking_value),
        0
    ) AS completed_booking_value_total

FROM ride360_staging.booking_records_classified AS c

GROUP BY
    c.batch_id,
    c.booking_status;


-- ============================================================
-- 03. VEHICLE PERFORMANCE MART
-- Grain: Batch + Vehicle Type
-- ============================================================

CREATE OR REPLACE VIEW
    ride360_analytics.vehicle_performance
AS
SELECT
    c.batch_id,

    COALESCE(
        c.vehicle_type,
        'MISSING'
    ) AS vehicle_type,

    COUNT(*)::BIGINT AS total_booking_records,

    COUNT(*) FILTER (
        WHERE c.is_completed
    )::BIGINT AS completed_bookings,

    COUNT(*) FILTER (
        WHERE c.is_cancelled
    )::BIGINT AS cancelled_bookings,

    COUNT(*) FILTER (
        WHERE c.is_no_driver_found
    )::BIGINT AS no_driver_found_bookings,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE c.is_completed
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS completion_rate_pct,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE c.is_cancelled
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS cancellation_rate_pct,

    COALESCE(
        SUM(c.completed_booking_value),
        0
    ) AS completed_booking_value_total,

    ROUND(
        AVG(c.ride_distance) FILTER (
            WHERE c.is_completed
        ),
        2
    ) AS avg_completed_ride_distance,

    ROUND(
        AVG(c.driver_rating) FILTER (
            WHERE c.is_completed
        ),
        2
    ) AS avg_driver_rating,

    ROUND(
        AVG(c.customer_rating) FILTER (
            WHERE c.is_completed
        ),
        2
    ) AS avg_customer_rating

FROM ride360_staging.booking_records_classified AS c

GROUP BY
    c.batch_id,
    c.vehicle_type;


-- ============================================================
-- 04. CANCELLATION REASONS MART
-- Grain: Batch + Cancellation Actor + Reason
-- ============================================================

CREATE OR REPLACE VIEW
    ride360_analytics.cancellation_reasons
AS
SELECT
    c.batch_id,

    'Customer'::TEXT AS cancellation_actor,

    COALESCE(
        c.customer_cancellation_reason,
        'NOT PROVIDED'
    ) AS cancellation_reason,

    COUNT(*)::BIGINT AS cancellation_records

FROM ride360_staging.booking_records_classified AS c

WHERE c.is_cancelled_by_customer

GROUP BY
    c.batch_id,
    c.customer_cancellation_reason

UNION ALL

SELECT
    c.batch_id,

    'Driver'::TEXT AS cancellation_actor,

    COALESCE(
        c.driver_cancellation_reason,
        'NOT PROVIDED'
    ) AS cancellation_reason,

    COUNT(*)::BIGINT AS cancellation_records

FROM ride360_staging.booking_records_classified AS c

WHERE c.is_cancelled_by_driver

GROUP BY
    c.batch_id,
    c.driver_cancellation_reason;


-- ============================================================
-- 05. PAYMENT METHOD MART
-- Grain: Batch + Payment Method
-- ============================================================
-- Payment method counts describe source records.
-- They are not equivalent to successful payments.
-- ============================================================

CREATE OR REPLACE VIEW
    ride360_analytics.payment_method_summary
AS
SELECT
    c.batch_id,

    COALESCE(
        c.payment_method,
        'MISSING'
    ) AS payment_method,

    COUNT(*)::BIGINT AS total_booking_records,

    COUNT(*) FILTER (
        WHERE c.is_completed
    )::BIGINT AS completed_bookings,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE c.is_completed
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS completion_rate_pct,

    COALESCE(
        SUM(c.completed_booking_value),
        0
    ) AS completed_booking_value_total

FROM ride360_staging.booking_records_classified AS c

GROUP BY
    c.batch_id,
    c.payment_method;


-- ============================================================
-- 06. PICKUP LOCATION PERFORMANCE
-- Grain: Batch + Pickup Location
-- ============================================================

CREATE OR REPLACE VIEW
    ride360_analytics.pickup_location_performance
AS
SELECT
    c.batch_id,

    COALESCE(
        c.pickup_location,
        'MISSING'
    ) AS pickup_location,

    COUNT(*)::BIGINT AS total_booking_records,

    COUNT(*) FILTER (
        WHERE c.is_completed
    )::BIGINT AS completed_bookings,

    COUNT(*) FILTER (
        WHERE c.is_cancelled
    )::BIGINT AS cancelled_bookings,

    COUNT(*) FILTER (
        WHERE c.is_no_driver_found
    )::BIGINT AS no_driver_found_bookings,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE c.is_completed
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS completion_rate_pct,

    COALESCE(
        SUM(c.completed_booking_value),
        0
    ) AS completed_booking_value_total

FROM ride360_staging.booking_records_classified AS c

GROUP BY
    c.batch_id,
    c.pickup_location;


-- ============================================================
-- 07. ROUTE PERFORMANCE
-- Grain: Batch + Pickup + Drop Location
-- ============================================================

CREATE OR REPLACE VIEW
    ride360_analytics.route_performance
AS
SELECT
    c.batch_id,

    COALESCE(
        c.pickup_location,
        'MISSING'
    ) AS pickup_location,

    COALESCE(
        c.drop_location,
        'MISSING'
    ) AS drop_location,

    COUNT(*)::BIGINT AS total_booking_records,

    COUNT(*) FILTER (
        WHERE c.is_completed
    )::BIGINT AS completed_bookings,

    COUNT(*) FILTER (
        WHERE c.is_cancelled
    )::BIGINT AS cancelled_bookings,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE c.is_completed
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS completion_rate_pct,

    COALESCE(
        SUM(c.completed_booking_value),
        0
    ) AS completed_booking_value_total,

    ROUND(
        AVG(c.ride_distance) FILTER (
            WHERE c.is_completed
        ),
        2
    ) AS avg_completed_ride_distance

FROM ride360_staging.booking_records_classified AS c

GROUP BY
    c.batch_id,
    c.pickup_location,
    c.drop_location;


-- ============================================================
-- 08. DATA QUALITY SUMMARY
-- Grain: One row per batch
-- ============================================================

CREATE OR REPLACE VIEW
    ride360_analytics.data_quality_summary
AS
SELECT
    q.batch_id,

    COUNT(*)::BIGINT AS total_booking_records,

    COUNT(*) FILTER (
        WHERE q.missing_booking_id
    )::BIGINT AS missing_booking_id_records,

    COUNT(*) FILTER (
        WHERE q.has_repeated_booking_id
    )::BIGINT AS records_with_repeated_booking_id,

    COUNT(*) FILTER (
        WHERE q.unknown_booking_status
    )::BIGINT AS unknown_booking_status_records,

    COUNT(*) FILTER (
        WHERE q.invalid_booking_value
    )::BIGINT AS invalid_booking_value_records,

    COUNT(*) FILTER (
        WHERE q.invalid_ride_distance
    )::BIGINT AS invalid_ride_distance_records,

    COUNT(*) FILTER (
        WHERE q.invalid_driver_rating
    )::BIGINT AS invalid_driver_rating_records,

    COUNT(*) FILTER (
        WHERE q.invalid_customer_rating
    )::BIGINT AS invalid_customer_rating_records,

    COUNT(*) FILTER (
        WHERE q.negative_booking_value
    )::BIGINT AS negative_booking_value_records,

    COUNT(*) FILTER (
        WHERE q.negative_ride_distance
    )::BIGINT AS negative_ride_distance_records,

    COUNT(*) FILTER (
        WHERE q.driver_rating_out_of_range
    )::BIGINT AS driver_rating_out_of_range_records,

    COUNT(*) FILTER (
        WHERE q.customer_rating_out_of_range
    )::BIGINT AS customer_rating_out_of_range_records

FROM ride360_staging.booking_quality_flags AS q

GROUP BY
    q.batch_id;


-- ============================================================
-- 09. DUPLICATE BOOKING ID SUMMARY
-- Grain: One row per batch
-- ============================================================

CREATE OR REPLACE VIEW
    ride360_analytics.booking_id_duplication_summary
AS
SELECT
    b.batch_id,

    COUNT(o.booking_id) FILTER (
        WHERE o.occurrence_count > 1
    )::BIGINT AS repeated_booking_id_groups,

    COALESCE(
        SUM(o.occurrence_count) FILTER (
            WHERE o.occurrence_count > 1
        ),
        0
    )::BIGINT AS records_in_repeated_groups,

    COALESCE(
        SUM(o.occurrence_count - 1) FILTER (
            WHERE o.occurrence_count > 1
        ),
        0
    )::BIGINT AS extra_booking_id_occurrences

FROM ride360_audit.ingestion_batches AS b

LEFT JOIN ride360_staging.booking_id_occurrences AS o
    ON o.batch_id = b.batch_id

WHERE b.batch_status = 'COMPLETED'

GROUP BY
    b.batch_id;


-- ============================================================
-- 10. MART DOCUMENTATION
-- ============================================================

COMMENT ON VIEW
    ride360_analytics.executive_kpis IS
    'Batch-level booking KPIs; completed value is not revenue.';

COMMENT ON VIEW
    ride360_analytics.booking_status_summary IS
    'Booking status counts and percentage distribution.';

COMMENT ON VIEW
    ride360_analytics.vehicle_performance IS
    'Booking and service performance by vehicle type.';

COMMENT ON VIEW
    ride360_analytics.cancellation_reasons IS
    'Cancellation reason counts by responsible actor.';

COMMENT ON VIEW
    ride360_analytics.payment_method_summary IS
    'Booking records by reported payment method.';

COMMENT ON VIEW
    ride360_analytics.pickup_location_performance IS
    'Booking outcomes by pickup location.';

COMMENT ON VIEW
    ride360_analytics.route_performance IS
    'Booking outcomes by pickup and drop location.';

COMMENT ON VIEW
    ride360_analytics.data_quality_summary IS
    'Aggregated record-level quality flags per batch.';

COMMENT ON VIEW
    ride360_analytics.booking_id_duplication_summary IS
    'Repeated Booking ID statistics without deduplication.';


COMMIT;

-- ============================================================
-- END OF FILE
-- ============================================================
