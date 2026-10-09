
-- ============================================================
-- RIDE360 | PHASE 3.5
-- CUSTOMER, LOCATION AND ROUTE ANALYTICS
-- File: sql/customer_location_analytics.sql
-- ============================================================

BEGIN;

-- 1. Customer-level booking activity.
-- Customer ID is a source identifier, not a verified person ID.

CREATE OR REPLACE VIEW
    ride360_analytics.customer_booking_activity
AS
WITH source_records AS (
    SELECT
        t.batch_id,
        t.raw_record_id,

        NULLIF(
            BTRIM(r.source_payload ->> 'Customer ID'),
            ''
        ) AS customer_id,

        t.is_completed,
        t.is_cancelled,
        t.is_no_driver_found,
        t.completed_booking_value

    FROM ride360_staging.booking_records_temporal AS t

    INNER JOIN ride360_raw.booking_records AS r
        ON r.batch_id = t.batch_id
        AND r.raw_record_id = t.raw_record_id
)

SELECT
    batch_id,
    customer_id,

    COUNT(*)::BIGINT AS total_booking_records,

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

FROM source_records
WHERE customer_id IS NOT NULL
GROUP BY batch_id, customer_id;


-- 2. Customer booking frequency segments.
-- Segments reflect source-record frequency, not retention cohorts.

CREATE OR REPLACE VIEW
    ride360_analytics.customer_frequency_segments
AS
WITH segmented AS (
    SELECT
        batch_id,
        customer_id,
        total_booking_records,
        completed_bookings,
        completed_booking_value_total,

        CASE
            WHEN total_booking_records = 1
                THEN '1 booking'
            WHEN total_booking_records BETWEEN 2 AND 4
                THEN '2-4 bookings'
            WHEN total_booking_records BETWEEN 5 AND 9
                THEN '5-9 bookings'
            ELSE '10+ bookings'
        END AS frequency_segment,

        CASE
            WHEN total_booking_records = 1 THEN 1
            WHEN total_booking_records BETWEEN 2 AND 4 THEN 2
            WHEN total_booking_records BETWEEN 5 AND 9 THEN 3
            ELSE 4
        END AS segment_sort_order

    FROM ride360_analytics.customer_booking_activity
)

SELECT
    batch_id,
    frequency_segment,
    segment_sort_order,

    COUNT(*)::BIGINT AS customer_ids,

    SUM(total_booking_records)::BIGINT
        AS total_booking_records,

    SUM(completed_bookings)::BIGINT
        AS completed_bookings,

    COALESCE(
        SUM(completed_booking_value_total),
        0
    ) AS completed_booking_value_total

FROM segmented

GROUP BY
    batch_id,
    frequency_segment,
    segment_sort_order;


-- 3. Pickup location performance.

CREATE OR REPLACE VIEW
    ride360_analytics.pickup_demand_intelligence
AS
SELECT
    t.batch_id,

    COALESCE(
        NULLIF(
            BTRIM(r.source_payload ->> 'Pickup Location'),
            ''
        ),
        'Unknown'
    ) AS pickup_location,

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
        100.0 * COUNT(*) FILTER (
            WHERE t.is_no_driver_found
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS no_driver_found_rate_pct,

    COALESCE(
        SUM(t.completed_booking_value),
        0
    ) AS completed_booking_value_total

FROM ride360_staging.booking_records_temporal AS t

INNER JOIN ride360_raw.booking_records AS r
    ON r.batch_id = t.batch_id
    AND r.raw_record_id = t.raw_record_id

GROUP BY
    t.batch_id,
    COALESCE(
        NULLIF(
            BTRIM(r.source_payload ->> 'Pickup Location'),
            ''
        ),
        'Unknown'
    );


-- 4. Pickup-to-drop route performance.
-- Direction matters: A -> B is not the same as B -> A.

CREATE OR REPLACE VIEW
    ride360_analytics.route_demand_intelligence
AS
SELECT
    t.batch_id,

    COALESCE(
        NULLIF(
            BTRIM(r.source_payload ->> 'Pickup Location'),
            ''
        ),
        'Unknown'
    ) AS pickup_location,

    COALESCE(
        NULLIF(
            BTRIM(r.source_payload ->> 'Drop Location'),
            ''
        ),
        'Unknown'
    ) AS drop_location,

    COUNT(*)::BIGINT AS total_bookings,

    COUNT(*) FILTER (
        WHERE t.is_completed
    )::BIGINT AS completed_bookings,

    COUNT(*) FILTER (
        WHERE t.is_cancelled
    )::BIGINT AS cancelled_bookings,

    ROUND(
        100.0 * COUNT(*) FILTER (WHERE t.is_completed)
        / NULLIF(COUNT(*), 0),
        2
    ) AS completion_rate_pct,

    COALESCE(
        SUM(t.completed_booking_value),
        0
    ) AS completed_booking_value_total

FROM ride360_staging.booking_records_temporal AS t

INNER JOIN ride360_raw.booking_records AS r
    ON r.batch_id = t.batch_id
    AND r.raw_record_id = t.raw_record_id

GROUP BY
    t.batch_id,
    COALESCE(
        NULLIF(
            BTRIM(r.source_payload ->> 'Pickup Location'),
            ''
        ),
        'Unknown'
    ),
    COALESCE(
        NULLIF(
            BTRIM(r.source_payload ->> 'Drop Location'),
            ''
        ),
        'Unknown'
    );


COMMENT ON VIEW
    ride360_analytics.customer_booking_activity IS
    'Customer-ID-level source booking activity.';

COMMENT ON VIEW
    ride360_analytics.customer_frequency_segments IS
    'Customer ID booking-frequency distribution.';

COMMENT ON VIEW
    ride360_analytics.pickup_demand_intelligence IS
    'Pickup location demand and service outcomes.';

COMMENT ON VIEW
    ride360_analytics.route_demand_intelligence IS
    'Directional pickup-to-drop booking demand.';

COMMIT;
