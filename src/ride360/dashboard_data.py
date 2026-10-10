"""Secure PostgreSQL data access for the RIDE360 analytics dashboard."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, LiteralString, cast

import pandas as pd
import psycopg
from dotenv import dotenv_values
from psycopg import sql
from psycopg.rows import dict_row

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"

# Authoritative warehouse analytics views.
ALLOWED_VIEWS = {
    "executive": "ride360_analytics.executive_kpis",
    "daily": "ride360_analytics.daily_booking_trends",
    "monthly": "ride360_analytics.monthly_booking_trends",
    "weekday": "ride360_analytics.weekday_booking_demand",
    "hourly": "ride360_analytics.hourly_booking_demand",
    "daypart": "ride360_analytics.daypart_booking_demand",
    "heatmap": "ride360_analytics.weekday_hour_heatmap",
    "cancellations": (
        "ride360_analytics.monthly_cancellation_intelligence"
    ),
    "cancellation_reasons": (
        "ride360_analytics.cancellation_reason_intelligence"
    ),
    "hourly_risk": "ride360_analytics.hourly_service_risk",
    "vehicles": "ride360_analytics.monthly_vehicle_intelligence",
    "pickups": "ride360_analytics.pickup_demand_intelligence",
    "routes": "ride360_analytics.route_demand_intelligence",
    "customers": "ride360_analytics.customer_frequency_segments",
    "business": "ride360_analytics.business_insight_summary",
    "quality": "ride360_audit.phase3_quality_summary",
}


def cache_enabled() -> bool:
    """Return whether the dashboard should use materialized views."""
    return os.getenv("RIDE360_USE_CACHE", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def get_connection_config(
    env_path: Path | None = None,
) -> dict[str, Any]:
    """Read PostgreSQL settings with environment-variable overrides."""
    path = env_path or ENV_FILE

    if env_path is not None and not path.is_file():
        raise FileNotFoundError(f"Environment file not found: {path}")

    file_values = dotenv_values(path) if path.is_file() else {}

    def setting(*names: str, default: str | None = None) -> str | None:
        for name in names:
            value = os.environ.get(name) or file_values.get(name)
            if value:
                return str(value)
        return default

    host = setting("DB_HOST", "POSTGRES_HOST", default="localhost")
    port = setting("DB_PORT", "POSTGRES_PORT", default="5433")
    database = setting("DB_NAME", "POSTGRES_DB")
    user = setting("DB_USER", "POSTGRES_USER")
    password = setting("DB_PASSWORD", "POSTGRES_PASSWORD")

    if not database or not user or not password:
        raise ValueError(
            "Missing PostgreSQL database, user or password. "
            "Configure .env or environment variables."
        )

    return {
        "host": host,
        "port": int(port or "5433"),
        "dbname": database,
        "user": user,
        "password": password,
        "connect_timeout": 10,
    }


def fetch_dataframe(
    query: str,
    params: tuple[Any, ...] = (),
    config: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Execute a query in a read-only PostgreSQL transaction."""
    settings = config or get_connection_config()

    with (
        psycopg.connect(
            **settings,
            row_factory=cast(Any, dict_row),
            options="-c default_transaction_read_only=on",
        ) as connection,
        connection.cursor() as cursor,
    ):
        sql_query = sql.SQL(cast(LiteralString, query))
        cursor.execute(sql_query, params)
        records = cursor.fetchall()

    return pd.DataFrame(records)


def get_view_name(view_key: str) -> str:
    """Resolve an allowlisted analytics view or materialized cache."""
    if view_key not in ALLOWED_VIEWS:
        raise ValueError(f"Unsupported dashboard view: {view_key}")

    if cache_enabled():
        return f"ride360_cache.{view_key}"

    return ALLOWED_VIEWS[view_key]


def fetch_batches() -> pd.DataFrame:
    """Return available warehouse batches and booking counts."""
    view_name = get_view_name("executive")

    return fetch_dataframe(
        f"""
        SELECT
            batch_id,
            total_booking_records
        FROM {view_name}
        ORDER BY batch_id DESC
        """
    )


def fetch_view(
    view_key: str,
    batch_id: int,
) -> pd.DataFrame:
    """Read one batch from an allowlisted analytics source."""
    if view_key not in ALLOWED_VIEWS:
        raise ValueError(f"Unsupported dashboard view: {view_key}")

    if not isinstance(batch_id, int) or batch_id < 1:
        raise ValueError("batch_id must be a positive integer")

    view_name = get_view_name(view_key)

    return fetch_dataframe(
        f"SELECT * FROM {view_name} WHERE batch_id = %s",
        (batch_id,),
    )


def to_csv_bytes(dataframe: pd.DataFrame) -> bytes:
    """Serialize the displayed dataset for CSV download."""
    return dataframe.to_csv(index=False).encode("utf-8-sig")
