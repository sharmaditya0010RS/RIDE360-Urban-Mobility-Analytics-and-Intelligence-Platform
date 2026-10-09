
-- ============================================================
-- RIDE360 | PHASE 3.6
-- BUSINESS INSIGHTS AND RECONCILIATION
-- File: sql/business_insights.sql
-- ============================================================

BEGIN;

-- 1. Executive business insight summary.
-- One row per completed ingestion batch.

CREATE OR REPLACE VIEW
    ride360_analytics.business_insight_summary
AS
WITH peak_hours AS (
    SELECT
        batch_id,
        booking_hour,
        total_bookings,
        ROW_NUMBER() OVER (
            PARTITION BY batch_id
            ORDER BY total_bookings DESC, booking_hour
        ) AS position
    FROM ride360_analytics.hourly_booking_demand
),
peak_months AS (
    SELECT
        batch_id,
        booking_month_start,
        total_bookings,
        ROW_NUMBER() OVER (
            PARTITION BY batch_id
            ORDER BY total_bookings DESC, booking_month_start
        ) AS position
    FROM ride360_analytics.monthly_booking_trends
),
top_vehicles AS (
    SELECT
        batch_id,
        vehicle_type,
        total_booking_records,
        ROW_NUMBER() OVER (
            PARTITION BY batch_id
            ORDER BY total_booking_records DESC, vehicle_type
        ) AS position
    FROM ride360_analytics.vehicle_performance
),
top_pickups AS (
    SELECT
        batch_id,
        pickup_location,
        total_bookings,
        ROW_NUMBER() OVER (
            PARTITION BY batch_id
            ORDER BY total_bookings DESC, pickup_location
        ) AS position
    FROM ride360_analytics.pickup_demand_intelligence
)

SELECT
    k.batch_id,

    k.total_booking_records,
    k.completed_bookings,
    k.cancelled_bookings,
    k.completion_rate_pct,
    k.cancellation_rate_pct,
    k.completed_booking_value_total,

    ph.booking_hour AS peak_booking_hour,
    ph.total_bookings AS peak_hour_bookings,

    pm.booking_month_start AS peak_booking_month,
    pm.total_bookings AS peak_month_bookings,

    tv.vehicle_type AS highest_volume_vehicle,
    tv.total_booking_records AS highest_volume_vehicle_bookings,

    tp.pickup_location AS highest_volume_pickup,
    tp.total_bookings AS highest_volume_pickup_bookings

FROM ride360_analytics.executive_kpis AS k

LEFT JOIN peak_hours AS ph
    ON ph.batch_id = k.batch_id
    AND ph.position = 1

LEFT JOIN peak_months AS pm
    ON pm.batch_id = k.batch_id
    AND pm.position = 1

LEFT JOIN top_vehicles AS tv
    ON tv.batch_id = k.batch_id
    AND tv.position = 1

LEFT JOIN top_pickups AS tp
    ON tp.batch_id = k.batch_id
    AND tp.position = 1;


-- 2. Phase 3 cross-mart reconciliation.
-- One row per completed batch, per quality check.

CREATE OR REPLACE VIEW
    ride360_audit.phase3_quality_checks
AS
WITH base AS (
    SELECT
        k.batch_id,
        k.total_booking_records AS expected_records,
        k.completed_bookings AS expected_completed,
        k.cancelled_bookings AS expected_cancelled,
        k.completed_booking_value_total AS expected_value,

        q.valid_timestamp_records,
        q.invalid_timestamp_records,

        (
            SELECT SUM(d.total_bookings)
            FROM ride360_analytics.daily_booking_trends AS d
            WHERE d.batch_id = k.batch_id
        ) AS daily_records,

        (
            SELECT SUM(m.total_bookings)
            FROM ride360_analytics.monthly_booking_trends AS m
            WHERE m.batch_id = k.batch_id
        ) AS monthly_records,

        (
            SELECT SUM(h.total_bookings)
            FROM ride360_analytics.hourly_booking_demand AS h
            WHERE h.batch_id = k.batch_id
        ) AS hourly_records,

        (
            SELECT SUM(w.total_bookings)
            FROM ride360_analytics.weekday_booking_demand AS w
            WHERE w.batch_id = k.batch_id
        ) AS weekday_records,

        (
            SELECT SUM(p.total_bookings)
            FROM ride360_analytics.daypart_booking_demand AS p
            WHERE p.batch_id = k.batch_id
        ) AS daypart_records,

        (
            SELECT SUM(x.total_bookings)
            FROM ride360_analytics.weekday_hour_heatmap AS x
            WHERE x.batch_id = k.batch_id
        ) AS heatmap_records,

        (
            SELECT SUM(c.total_bookings)
            FROM ride360_analytics.monthly_cancellation_intelligence AS c
            WHERE c.batch_id = k.batch_id
        ) AS cancellation_mart_records,

        (
            SELECT SUM(c.total_cancellations)
            FROM ride360_analytics.monthly_cancellation_intelligence AS c
            WHERE c.batch_id = k.batch_id
        ) AS cancellation_mart_cancelled,

        (
            SELECT SUM(v.total_bookings)
            FROM ride360_analytics.monthly_vehicle_intelligence AS v
            WHERE v.batch_id = k.batch_id
        ) AS vehicle_records,

        (
            SELECT SUM(v.completed_booking_value_total)
            FROM ride360_analytics.monthly_vehicle_intelligence AS v
            WHERE v.batch_id = k.batch_id
        ) AS vehicle_completed_value,

        (
            SELECT SUM(p.total_bookings)
            FROM ride360_analytics.pickup_demand_intelligence AS p
            WHERE p.batch_id = k.batch_id
        ) AS pickup_records,

        (
            SELECT SUM(r.total_bookings)
            FROM ride360_analytics.route_demand_intelligence AS r
            WHERE r.batch_id = k.batch_id
        ) AS route_records,

        (
            SELECT SUM(c.cancellation_records)
            FROM ride360_analytics.cancellation_reason_intelligence AS c
            WHERE c.batch_id = k.batch_id
        ) AS reason_records,

        (
            SELECT COUNT(*)
            FROM ride360_staging.booking_records_temporal AS t
            WHERE t.batch_id = k.batch_id
        ) AS temporal_records,

        (
            SELECT COUNT(*)
            FROM ride360_staging.booking_records_temporal AS t
            WHERE t.batch_id = k.batch_id
              AND t.booking_timestamp IS NOT NULL
        ) AS nonnull_timestamps,

        (
            SELECT COUNT(*)
            FROM ride360_raw.booking_records AS r
            WHERE r.batch_id = k.batch_id
              AND NULLIF(
                  BTRIM(r.source_payload ->> 'Customer ID'),
                  ''
              ) IS NOT NULL
        ) AS known_customer_records,

        (
            SELECT COALESCE(SUM(c.total_booking_records), 0)
            FROM ride360_analytics.customer_booking_activity AS c
            WHERE c.batch_id = k.batch_id
        ) AS customer_activity_records,

        (
            SELECT COALESCE(SUM(s.total_booking_records), 0)
            FROM ride360_analytics.customer_frequency_segments AS s
            WHERE s.batch_id = k.batch_id
        ) AS customer_segment_records

    FROM ride360_analytics.executive_kpis AS k

    LEFT JOIN ride360_audit.temporal_quality_summary AS q
        ON q.batch_id = k.batch_id
),
checks AS (
    SELECT
        batch_id,
        'raw_to_temporal'::TEXT AS check_name,
        expected_records = temporal_records AS passed
    FROM base

    UNION ALL
    SELECT batch_id, 'valid_timestamp_partition',
        expected_records =
        COALESCE(valid_timestamp_records, 0)
        + COALESCE(invalid_timestamp_records, 0)
    FROM base

    UNION ALL
    SELECT batch_id, 'timestamp_nonnull_count',
        nonnull_timestamps = valid_timestamp_records
    FROM base

    UNION ALL
    SELECT batch_id, 'daily_booking_total',
        daily_records = valid_timestamp_records
        + (
            SELECT COUNT(*)
            FROM ride360_staging.booking_records_temporal AS t
            WHERE t.batch_id = base.batch_id
              AND t.booking_date IS NOT NULL
              AND t.booking_time IS NULL
        )
    FROM base

    UNION ALL
    SELECT batch_id, 'monthly_booking_total',
        monthly_records = daily_records
    FROM base

    UNION ALL
    SELECT batch_id, 'hourly_booking_total',
        hourly_records = (
            SELECT COUNT(*)
            FROM ride360_staging.booking_records_temporal AS t
            WHERE t.batch_id = base.batch_id
              AND t.booking_time IS NOT NULL
        )
    FROM base

    UNION ALL
    SELECT batch_id, 'weekday_booking_total',
        weekday_records = daily_records
    FROM base

    UNION ALL
    SELECT batch_id, 'daypart_booking_total',
        daypart_records = hourly_records
    FROM base

    UNION ALL
    SELECT batch_id, 'weekday_hour_heatmap_total',
        heatmap_records = valid_timestamp_records
    FROM base

    UNION ALL
    SELECT batch_id, 'monthly_cancellation_mart_total',
        cancellation_mart_records = monthly_records
    FROM base

    UNION ALL
    SELECT batch_id, 'monthly_cancellation_count',
        cancellation_mart_cancelled = expected_cancelled
        - (
            SELECT COUNT(*)
            FROM ride360_staging.booking_records_temporal AS t
            WHERE t.batch_id = base.batch_id
              AND t.is_cancelled
              AND t.booking_date IS NULL
        )
    FROM base

    UNION ALL
    SELECT batch_id, 'monthly_vehicle_total',
        vehicle_records = monthly_records
    FROM base

    UNION ALL
    SELECT batch_id, 'monthly_vehicle_value',
        vehicle_completed_value = (
            SELECT COALESCE(
                SUM(t.completed_booking_value), 0
            )
            FROM ride360_staging.booking_records_temporal AS t
            WHERE t.batch_id = base.batch_id
              AND t.booking_date IS NOT NULL
        )
    FROM base

    UNION ALL
    SELECT batch_id, 'pickup_location_total',
        pickup_records = expected_records
    FROM base

    UNION ALL
    SELECT batch_id, 'route_total',
        route_records = expected_records
    FROM base

    UNION ALL
    SELECT batch_id, 'cancellation_reason_total',
        reason_records = expected_cancelled
    FROM base

    UNION ALL
    SELECT batch_id, 'customer_activity_total',
        customer_activity_records = known_customer_records
    FROM base

    UNION ALL
    SELECT batch_id, 'customer_frequency_segment_total',
        customer_segment_records = known_customer_records
    FROM base
)

SELECT
    batch_id,
    check_name,
    COALESCE(passed, FALSE) AS passed,
    CASE
        WHEN COALESCE(passed, FALSE)
            THEN 'PASS'
        ELSE 'FAIL'
    END AS check_status

FROM checks;


-- 3. Quality summary.

CREATE OR REPLACE VIEW
    ride360_audit.phase3_quality_summary
AS
SELECT
    batch_id,
    COUNT(*)::BIGINT AS total_checks,
    COUNT(*) FILTER (
        WHERE passed
    )::BIGINT AS passed_checks,
    COUNT(*) FILTER (
        WHERE NOT passed
    )::BIGINT AS failed_checks,
    BOOL_AND(passed) AS all_checks_passed
FROM ride360_audit.phase3_quality_checks
GROUP BY batch_id;


COMMENT ON VIEW
    ride360_analytics.business_insight_summary IS
    'Executive booking KPIs and highest-volume segments.';

COMMENT ON VIEW
    ride360_audit.phase3_quality_checks IS
    'Cross-mart reconciliation checks for Phase 3 analytics.';

COMMENT ON VIEW
    ride360_audit.phase3_quality_summary IS
    'Aggregated Phase 3 reconciliation status.';

COMMIT;
