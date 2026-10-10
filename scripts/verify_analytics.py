"""Verify cached analytics match authoritative source views."""

from __future__ import annotations

import argparse
import re

import psycopg
from psycopg import sql

from ride360.dashboard_data import (
    ALLOWED_VIEWS,
    get_connection_config,
)

SAFE = re.compile(r"^[a-z][a-z0-9_]*$")


def safe_name(value: str) -> str:
    if not SAFE.fullmatch(value):
        raise ValueError(f"Invalid identifier: {value}")
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, default=1)
    parser.add_argument(
        "--include-quality",
        action="store_true",
    )
    args = parser.parse_args()

    if args.batch < 1:
        parser.error("--batch must be positive")

    failures = []

    with psycopg.connect(**get_connection_config()) as conn, conn.cursor() as cursor:
        for key, source in ALLOWED_VIEWS.items():
            if key == "quality" and not args.include_quality:
                print("SKIP quality (expensive source query)")
                continue

            schema, view = source.split(".", 1)
            source_name = sql.Identifier(
                safe_name(schema),
                safe_name(view),
            )
            cache_name = sql.Identifier(
                "ride360_cache",
                safe_name(key),
            )

            query = sql.SQL(
                """
                    SELECT NOT EXISTS (
                        (
                            SELECT * FROM {source_name}
                            WHERE batch_id = %s
                            EXCEPT ALL
                            SELECT * FROM {cache_name}
                            WHERE batch_id = %s
                        )
                        UNION ALL
                        (
                            SELECT * FROM {cache_name}
                            WHERE batch_id = %s
                            EXCEPT ALL
                            SELECT * FROM {source_name}
                            WHERE batch_id = %s
                        )
                    )
                    """
            ).format(
                source_name=source_name,
                cache_name=cache_name,
            )

            try:
                cursor.execute(
                    query,
                    (args.batch,) * 4,
                )
                row = cursor.fetchone()
                if row is None:
                    raise RuntimeError(
                        f"Verification query for {key} returned no rows."
                    )
                matched = bool(row[0])
            except psycopg.Error:
                conn.rollback()
                raise

            print(
                f"{key}: "
                f"{'PASS' if matched else 'FAIL'}"
            )

            if not matched:
                failures.append(key)

    if failures:
        raise SystemExit(
            f"Cache mismatches: {', '.join(failures)}"
        )

    print("All checked analytics match.")


if __name__ == "__main__":
    main()
