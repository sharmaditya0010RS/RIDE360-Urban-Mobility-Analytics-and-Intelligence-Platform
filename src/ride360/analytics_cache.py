"""Build and refresh materialized analytics for the dashboard."""

from __future__ import annotations

import argparse
import re
from time import perf_counter

import psycopg
from psycopg import sql

from ride360.dashboard_data import ALLOWED_VIEWS, get_connection_config

CACHE_SCHEMA = "ride360_cache"
SAFE_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")


def identifier(value: str) -> str:
    if not SAFE_IDENTIFIER.fullmatch(value):
        raise ValueError(f"Unsafe SQL identifier: {value}")
    return value


def build_cache() -> None:
    """Build cache objects without replacing source analytics views."""
    with psycopg.connect(**get_connection_config()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("CREATE SCHEMA IF NOT EXISTS {}")
                .format(sql.Identifier(CACHE_SCHEMA))
            )
        connection.commit()

        for key, source in ALLOWED_VIEWS.items():
            identifier(key)
            schema, view = source.split(".", maxsplit=1)
            identifier(schema)
            identifier(view)

            cache_name = f"{CACHE_SCHEMA}.{key}"
            started = perf_counter()

            print(f"Building {cache_name}...", flush=True)

            # One transaction per view: an interrupted build does not
            # leave a partially refreshed view.
            with connection.transaction(), connection.cursor() as cursor:
                cursor.execute(
                    sql.SQL(
                        "CREATE MATERIALIZED VIEW IF NOT EXISTS {} AS "
                        "SELECT * FROM {}.{} WITH NO DATA"
                    ).format(
                        sql.Identifier(CACHE_SCHEMA, key),
                        sql.Identifier(schema),
                        sql.Identifier(view),
                    )
                )

                cursor.execute(
                    sql.SQL("REFRESH MATERIALIZED VIEW {}")
                    .format(sql.Identifier(CACHE_SCHEMA, key))
                )

                index_name = f"idx_cache_{key}_batch"
                cursor.execute(
                    sql.SQL("CREATE INDEX IF NOT EXISTS {} ON {} (batch_id)")
                    .format(
                        sql.Identifier(index_name),
                        sql.Identifier(CACHE_SCHEMA, key),
                    )
                )

                cursor.execute(
                    sql.SQL("ANALYZE {}")
                    .format(sql.Identifier(CACHE_SCHEMA, key))
                )

            print(
                f"Completed {key}: "
                f"{perf_counter() - started:.2f}s",
                flush=True,
            )


def refresh_cache() -> None:
    """Refresh existing cache objects from authoritative SQL views."""
    with psycopg.connect(**get_connection_config()) as connection:
        for key in ALLOWED_VIEWS:
            identifier(key)
            cache_name = f"{CACHE_SCHEMA}.{key}"

            print(f"Refreshing {cache_name}...", flush=True)

            with connection.transaction(), connection.cursor() as cursor:
                cursor.execute(
                    sql.SQL("REFRESH MATERIALIZED VIEW {}")
                    .format(sql.Identifier(CACHE_SCHEMA, key))
                )
                cursor.execute(
                    sql.SQL("ANALYZE {}")
                    .format(sql.Identifier(CACHE_SCHEMA, key))
                )

            print(f"Refreshed {key}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=["build", "refresh"],
    )
    args = parser.parse_args()

    if args.action == "build":
        build_cache()
    else:
        refresh_cache()


if __name__ == "__main__":
    main()
