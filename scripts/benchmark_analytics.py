"""Benchmark dashboard analytics and export performance results."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from ride360.dashboard_data import (
    ALLOWED_VIEWS,
    fetch_batches,
    fetch_view,
)

ROOT = Path(__file__).resolve().parents[1]


def benchmark(mode: str, include_quality: bool) -> dict:
    os.environ["RIDE360_USE_CACHE"] = (
        "1" if mode == "cached" else "0"
    )

    batches = fetch_batches()

    if batches.empty:
        raise RuntimeError("No warehouse batches available")

    batch_id = int(batches.iloc[0]["batch_id"])
    results = []

    for key in ALLOWED_VIEWS:
        if key == "quality" and not include_quality:
            continue

        started = perf_counter()

        try:
            dataframe = fetch_view(key, batch_id)
            result = {
                "view": key,
                "status": "OK",
                "rows": len(dataframe),
                "seconds": round(
                    perf_counter() - started, 3
                ),
            }
        except Exception as exc:  # noqa: BLE001
            result = {
                "view": key,
                "status": "ERROR",
                "error_type": type(exc).__name__,
            }

        results.append(result)
        print(result, flush=True)

    return {
        "created_utc": datetime.now(UTC).isoformat(),
        "mode": mode,
        "batch_id": batch_id,
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["original", "cached"],
        default="cached",
    )
    parser.add_argument(
        "--include-quality",
        action="store_true",
    )
    args = parser.parse_args()

    report = benchmark(args.mode, args.include_quality)

    target = (
        ROOT
        / "reports"
        / "exports"
        / f"benchmark_{args.mode}.json"
    )

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print(f"Saved: {target}")


if __name__ == "__main__":
    main()
