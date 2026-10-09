
-- ============================================================
-- RIDE360 | WAREHOUSE QUALITY CHECKS
-- File: sql/warehouse_quality_checks.sql
-- PostgreSQL 16+
-- ============================================================

BEGIN;

CREATE OR REPLACE VIEW
    ride360_audit.warehouse_quality_checks
AS
WITH raw_counts AS (
    SELECT
        batch_id,
        COUNT(*)::BIGINT AS raw_records
    FROM ride360_raw.booking_records
    GROUP BY batch_id
),
staging_counts AS (
    SELECT
        batch_id,
        COUNT(*)::BIGINT AS staging_records,
        COUNT(*) FILTER (
            WHERE is_completed
        )::BIGINT AS completed_records,
        COUNT(*) FILTER (
            WHERE is_cancelled
        )::BIGINT AS cancelled_records,
        COUNT(*) FILTER (
            WHERE is_cancelled_by_customer
        )::BIGINT AS customer_cancelled_records,
        COUNT(*) FILTER (
            WHERE is_cancelled_by_driver
        )::BIGINT AS driver_cancelled_records,
        COUNT(*) FILTER (
            WHERE is_incomplete
        )::BIGINT AS incomplete_records,
        COUNT(*) FILTER (
            WHERE is_no_driver_found
        )::BIGINT AS no_driver_found_records,
        COUNT(*) FILTER (
            WHERE NOT has_known_booking_status
        )::BIGINT AS unknown_status_records,
        COALESCE(
            SUM(completed_booking_value),
            0
        ) AS completed_booking_value_total,
        COUNT(DISTINCT booking_id)::BIGINT
            AS distinct_booking_ids
    FROM ride360_staging.booking_records_classified
    GROUP BY batch_id
),
status_counts AS (
    SELECT
        batch_id,
        SUM(booking_records)::BIGINT
            AS status_summary_records
    FROM ride360_analytics.booking_status_summary
    GROUP BY batch_id
),
vehicle_counts AS (
    SELECT
        batch_id,
        SUM(total_booking_records)::BIGINT
            AS vehicle_summary_records
    FROM ride360_analytics.vehicle_performance
    GROUP BY batch_id
),
payment_counts AS (
    SELECT
        batch_id,
        SUM(total_booking_records)::BIGINT
            AS payment_summary_records
    FROM ride360_analytics.payment_method_summary
    GROUP BY batch_id
),
pickup_counts AS (
    SELECT
        batch_id,
        SUM(total_booking_records)::BIGINT
            AS pickup_summary_records
    FROM ride360_analytics.pickup_location_performance
    GROUP BY batch_id
),
route_counts AS (
    SELECT
        batch_id,
        SUM(total_booking_records)::BIGINT
            AS route_summary_records
    FROM ride360_analytics.route_performance
    GROUP BY batch_id
),
cancellation_counts AS (
    SELECT
        batch_id,
        SUM(cancellation_records)::BIGINT
            AS cancellation_reason_records
    FROM ride360_analytics.cancellation_reasons
    GROUP BY batch_id
),
base AS (
    SELECT
        b.batch_id,
        b.batch_status,
        b.source_record_count,
        b.loaded_record_count,

        COALESCE(r.raw_records, 0)
            AS raw_records,

        COALESCE(s.staging_records, 0)
            AS staging_records,

        COALESCE(k.total_booking_records, 0)
            AS analytics_records,

        COALESCE(s.completed_records, 0)
            AS staging_completed,

        COALESCE(s.cancelled_records, 0)
            AS staging_cancelled,

        COALESCE(s.customer_cancelled_records, 0)
            AS staging_customer_cancelled,

        COALESCE(s.driver_cancelled_records, 0)
            AS staging_driver_cancelled,

        COALESCE(s.incomplete_records, 0)
            AS staging_incomplete,

        COALESCE(s.no_driver_found_records, 0)
            AS staging_no_driver_found,

        COALESCE(s.unknown_status_records, 0)
            AS staging_unknown_status,

        COALESCE(
            s.completed_booking_value_total, 0
        ) AS staging_completed_value,

        COALESCE(s.distinct_booking_ids, 0)
            AS staging_distinct_ids,

        k.completed_bookings AS mart_completed,
        k.cancelled_bookings AS mart_cancelled,

        k.customer_cancelled_bookings
            AS mart_customer_cancelled,

        k.driver_cancelled_bookings
            AS mart_driver_cancelled,

        k.incomplete_bookings AS mart_incomplete,

        k.no_driver_found_bookings
            AS mart_no_driver_found,

        k.unknown_status_bookings
            AS mart_unknown_status,

        k.completed_booking_value_total
            AS mart_completed_value,

        k.distinct_booking_ids
            AS mart_distinct_ids,

        COALESCE(st.status_summary_records, 0)
            AS status_summary_records,

        COALESCE(v.vehicle_summary_records, 0)
            AS vehicle_summary_records,

        COALESCE(p.payment_summary_records, 0)
            AS payment_summary_records,

        COALESCE(l.pickup_summary_records, 0)
            AS pickup_summary_records,

        COALESCE(rt.route_summary_records, 0)
            AS route_summary_records,

        COALESCE(c.cancellation_reason_records, 0)
            AS cancellation_reason_records,

        d.repeated_booking_id_groups,
        d.records_in_repeated_groups,
        d.extra_booking_id_occurrences

    FROM ride360_audit.ingestion_batches AS b

    LEFT JOIN raw_counts AS r
        ON r.batch_id = b.batch_id

    LEFT JOIN staging_counts AS s
        ON s.batch_id = b.batch_id

    LEFT JOIN ride360_analytics.executive_kpis AS k
        ON k.batch_id = b.batch_id

    LEFT JOIN status_counts AS st
        ON st.batch_id = b.batch_id

    LEFT JOIN vehicle_counts AS v
        ON v.batch_id = b.batch_id

    LEFT JOIN payment_counts AS p
        ON p.batch_id = b.batch_id

    LEFT JOIN pickup_counts AS l
        ON l.batch_id = b.batch_id

    LEFT JOIN route_counts AS rt
        ON rt.batch_id = b.batch_id

    LEFT JOIN cancellation_counts AS c
        ON c.batch_id = b.batch_id

    LEFT JOIN
        ride360_analytics.booking_id_duplication_summary AS d
        ON d.batch_id = b.batch_id

    WHERE b.batch_status = 'COMPLETED'
),
checks AS (
    SELECT
        batch_id,
        'source_to_raw_count'::TEXT AS check_name,
        (
            source_record_count = raw_records
            AND loaded_record_count = raw_records
        ) AS passed,
        source_record_count::TEXT AS expected_value,
        raw_records::TEXT AS actual_value
    FROM base

    UNION ALL

    SELECT
        batch_id,
        'raw_to_staging_count',
        raw_records = staging_records,
        raw_records::TEXT,
        staging_records::TEXT
    FROM base

    UNION ALL

    SELECT
        batch_id,
        'staging_to_analytics_count',
        staging_records = analytics_records,
        staging_records::TEXT,
        analytics_records::TEXT
    FROM base

    UNION ALL

    SELECT
        batch_id,
        'completed_booking_count',
        staging_completed = mart_completed,
        staging_completed::TEXT,
        mart_completed::TEXT
    FROM base

    UNION ALL

    SELECT
        batch_id,
        'cancelled_booking_count',
        staging_cancelled = mart_cancelled,
        staging_cancelled::TEXT,
        mart_cancelled::TEXT
    FROM base

    UNION ALL

    SELECT
        batch_id,
        'customer_cancellation_count',
        staging_customer_cancelled = mart_customer_cancelled,
        staging_customer_cancelled::TEXT,
        mart_customer_cancelled::TEXT
    FROM base

    UNION ALL

    SELECT
        batch_id,
        'driver_cancellation_count',
        staging_driver_cancelled = mart_driver_cancelled,
        staging_driver_cancelled::TEXT,
        mart_driver_cancelled::TEXT
    FROM base

    UNION ALL

    SELECT
        batch_id,
        'incomplete_booking_count',
        staging_incomplete = mart_incomplete,
        staging_incomplete::TEXT,
        mart_incomplete::TEXT
    FROM base

    UNION ALL

    SELECT
        batch_id,
        'no_driver_found_count',
        staging_no_driver_found = mart_no_driver_found,
        staging_no_driver_found::TEXT,
        mart_no_driver_found::TEXT
    FROM base

    UNION ALL

    SELECT
        batch_id,
        'unknown_booking_status_count',
        staging_unknown_status = mart_unknown_status,
        staging_unknown_status::TEXT,
        mart_unknown_status::TEXT
    FROM base

    UNION ALL

    SELECT
        batch_id,
        'completed_booking_value',
        staging_completed_value = mart_completed_value,
        staging_completed_value::TEXT,
        mart_completed_value::TEXT
    FROM base

    UNION ALL

    SELECT
        batch_id,
        'distinct_booking_ids',
        staging_distinct_ids = mart_distinct_ids,
        staging_distinct_ids::TEXT,
        mart_distinct_ids::TEXT
    FROM base

    UNION ALL

    SELECT
        batch_id,
        'status_distribution_count',
        staging_records = status_summary_records,
        staging_records::TEXT,
        status_summary_records::TEXT
    FROM base

    UNION ALL

    SELECT
        batch_id,
        'vehicle_distribution_count',
        staging_records = vehicle_summary_records,
        staging_records::TEXT,
        vehicle_summary_records::TEXT
    FROM base

    UNION ALL

    SELECT
        batch_id,
        'payment_distribution_count',
        staging_records = payment_summary_records,
        staging_records::TEXT,
        payment_summary_records::TEXT
    FROM base

    UNION ALL

    SELECT
        batch_id,
        'pickup_distribution_count',
        staging_records = pickup_summary_records,
        staging_records::TEXT,
        pickup_summary_records::TEXT
    FROM base

    UNION ALL

    SELECT
        batch_id,
        'route_distribution_count',
        staging_records = route_summary_records,
        staging_records::TEXT,
        route_summary_records::TEXT
    FROM base

    UNION ALL

    SELECT
        batch_id,
        'cancellation_reason_count',
        staging_cancelled = cancellation_reason_records,
        staging_cancelled::TEXT,
        cancellation_reason_records::TEXT
    FROM base

    UNION ALL

    SELECT
        batch_id,
        'status_partition_count',
        staging_records = (
            staging_completed
            + staging_cancelled
            + staging_incomplete
            + staging_no_driver_found
            + staging_unknown_status
        ),
        staging_records::TEXT,
        (
            staging_completed
            + staging_cancelled
            + staging_incomplete
            + staging_no_driver_found
            + staging_unknown_status
        )::TEXT
    FROM base

    UNION ALL

    SELECT
        batch_id,
        'duplicate_occurrence_identity',
        (
            repeated_booking_id_groups IS NOT NULL
            AND records_in_repeated_groups IS NOT NULL
            AND extra_booking_id_occurrences IS NOT NULL
            AND records_in_repeated_groups
                - repeated_booking_id_groups
                = extra_booking_id_occurrences
        ),
        COALESCE(
            (
                records_in_repeated_groups
                - repeated_booking_id_groups
            )::TEXT,
            'NULL'
        ),
        COALESCE(
            extra_booking_id_occurrences::TEXT,
            'NULL'
        )
    FROM base
)

SELECT
    batch_id,
    check_name,
    COALESCE(passed, FALSE) AS passed,
    expected_value,
    actual_value,
    CASE
        WHEN COALESCE(passed, FALSE)
        THEN 'PASS'
        ELSE 'FAIL'
    END AS check_status
FROM checks;


CREATE OR REPLACE VIEW
    ride360_audit.warehouse_quality_summary
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
FROM ride360_audit.warehouse_quality_checks
GROUP BY batch_id;


COMMENT ON VIEW
    ride360_audit.warehouse_quality_checks IS
    'Batch-level cross-layer reconciliation checks.';


COMMENT ON VIEW
    ride360_audit.warehouse_quality_summary IS
    'Aggregated warehouse quality status per completed batch.';


COMMIT;
