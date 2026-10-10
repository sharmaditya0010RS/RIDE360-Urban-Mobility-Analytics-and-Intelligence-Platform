"""Phase 5 baseline: time individual read-only analytics queries."""
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ride360.dashboard_data import ALLOWED_VIEWS, fetch_batches, fetch_view


def main() -> None:
    batches = fetch_batches()
    if batches.empty:
        raise SystemExit("No batches available for benchmarking")
    batch = int(batches.iloc[0]["batch_id"])
    results = []
    for key in ALLOWED_VIEWS:
        started = perf_counter()
        try:
            df = fetch_view(key, batch)
        except Exception as exc:  # noqa: BLE001 - record individual view failures
            results.append({"view": key, "status": "ERROR", "error_type": type(exc).__name__})
        else:
            results.append({
                "view": key,
                "status": "OK",
                "rows": len(df),
                "seconds": round(perf_counter() - started, 3),
            })
        print(results[-1], flush=True)
    output = {
        "created_utc": datetime.now(UTC).isoformat(),
        "batch_id": batch,
        "results": results,
    }
    target = ROOT / "reports" / "exports" / "dashboard_benchmark.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Benchmark saved to {target}")


if __name__ == "__main__":
    main()
