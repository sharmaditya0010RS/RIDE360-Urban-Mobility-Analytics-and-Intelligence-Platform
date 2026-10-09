
"""RIDE360 Phase 3 analytical warehouse integration tests."""

from pathlib import Path

import psycopg
import pytest

from ride360.warehouse_pipeline import get_database_config

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"


@pytest.fixture(scope="module")
def db():
    """Connect to the local PostgreSQL warehouse."""
    if not ENV_PATH.is_file():
        pytest.skip("PostgreSQL .env not available")

    config = get_database_config(ENV_PATH)

    try:
        connection = psycopg.connect(**config)
    except psycopg.OperationalError:
        pytest.skip("PostgreSQL is not reachable")

    with connection:
        yield connection


def scalar(db, query):
    """Execute a scalar read-only SQL query."""
    with db.cursor() as cursor:
        cursor.execute(query)
        row = cursor.fetchone()
        assert row is not None
        return row[0]


def test_temporal_record_preservation(db):
    assert scalar(
        db,
        """
        SELECT COUNT(*)
        FROM ride360_staging.booking_records_temporal
        WHERE batch_id = 1
        """
    ) == 150000


def test_all_source_timestamps_valid(db):
    assert scalar(
        db,
        """
        SELECT invalid_timestamp_records
        FROM ride360_audit.temporal_quality_summary
        WHERE batch_id = 1
        """
    ) == 0


@pytest.mark.parametrize(
    "view_name",
    [
        "daily_booking_trends",
        "monthly_booking_trends",
        "weekday_booking_demand",
        "hourly_booking_demand",
        "daypart_booking_demand",
        "weekday_hour_heatmap",
        "monthly_cancellation_intelligence",
        "hourly_service_risk",
        "monthly_vehicle_intelligence",
        "pickup_demand_intelligence",
        "route_demand_intelligence",
    ],
)
def test_booking_mart_reconciles_to_source(db, view_name):
    """Every Batch 1 booking belongs to exactly one group."""
    allowed_views = {
        "daily_booking_trends",
        "monthly_booking_trends",
        "weekday_booking_demand",
        "hourly_booking_demand",
        "daypart_booking_demand",
        "weekday_hour_heatmap",
        "monthly_cancellation_intelligence",
        "hourly_service_risk",
        "monthly_vehicle_intelligence",
        "pickup_demand_intelligence",
        "route_demand_intelligence",
    }

    assert view_name in allowed_views

    result = scalar(
        db,
        f"""
        SELECT SUM(total_bookings)
        FROM ride360_analytics.{view_name}
        WHERE batch_id = 1
        """,
    )

    assert result == 150000


def test_cancellation_reasons_reconcile(db):
    assert scalar(
        db,
        """
        SELECT SUM(cancellation_records)
        FROM ride360_analytics.cancellation_reason_intelligence
        WHERE batch_id = 1
        """
    ) == 37500


def test_customer_activity_preserves_known_customer_records(db):
    result = scalar(
        db,
        """
        SELECT COALESCE(SUM(total_booking_records), 0)
        FROM ride360_analytics.customer_booking_activity
        WHERE batch_id = 1
        """
    )

    source = scalar(
        db,
        """
        SELECT COUNT(*)
        FROM ride360_raw.booking_records
        WHERE batch_id = 1
          AND NULLIF(
              BTRIM(source_payload ->> 'Customer ID'),
              ''
          ) IS NOT NULL
        """,
    )

    assert result == source


def test_customer_segments_reconcile(db):
    activity = scalar(
        db,
        """
        SELECT COALESCE(SUM(total_booking_records), 0)
        FROM ride360_analytics.customer_booking_activity
        WHERE batch_id = 1
        """,
    )

    segments = scalar(
        db,
        """
        SELECT COALESCE(SUM(total_booking_records), 0)
        FROM ride360_analytics.customer_frequency_segments
        WHERE batch_id = 1
        """,
    )

    assert activity == segments


def test_phase3_quality_checks_pass(db):
    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                total_checks,
                passed_checks,
                failed_checks,
                all_checks_passed
            FROM ride360_audit.phase3_quality_summary
            WHERE batch_id = 1
            """
        )

        row = cursor.fetchone()

    assert row == (18, 18, 0, True)


def test_peak_hour_is_18(db):
    assert scalar(
        db,
        """
        SELECT peak_booking_hour
        FROM ride360_analytics.business_insight_summary
        WHERE batch_id = 1
        """
    ) == 18


def test_peak_month_is_july(db):
    assert scalar(
        db,
        """
        SELECT peak_booking_month
        FROM ride360_analytics.business_insight_summary
        WHERE batch_id = 1
        """
    ).month == 7


def test_highest_volume_vehicle_is_auto(db):
    assert scalar(
        db,
        """
        SELECT highest_volume_vehicle
        FROM ride360_analytics.business_insight_summary
        WHERE batch_id = 1
        """
    ) == "Auto"


def test_executive_total_unchanged(db):
    assert scalar(
        db,
        """
        SELECT total_booking_records
        FROM ride360_analytics.executive_kpis
        WHERE batch_id = 1
        """
    ) == 150000
