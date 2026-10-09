
"""Unified Phase 1 validation and reporting for RIDE360."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from ride360.business_rules import export_business_rules
from ride360.event_rules import export_event_rules
from ride360.metadata import export_metadata
from ride360.profiling import export_profile, load_bookings
from ride360.quality import export_quality

LAYER_ORDER = (
    "structural",
    "business",
    "events",
    "metadata",
)

VALID_STATUSES = {"PASS", "WARN", "FAIL"}


def combined_status(statuses: list[str]) -> str:
    """Return the most severe status across validation layers."""
    if not statuses:
        raise ValueError("At least one validation status is required")

    unknown = set(statuses) - VALID_STATUSES

    if unknown:
        raise ValueError(f"Unknown validation statuses: {sorted(unknown)}")

    if "FAIL" in statuses:
        return "FAIL"

    if "WARN" in statuses:
        return "WARN"

    return "PASS"


def build_manifest(
    *,
    source: Path,
    rows: int,
    columns: int,
    layers: dict[str, dict],
    kpis: dict,
) -> dict:
    """Create the final machine-readable Phase 1 manifest."""
    missing = set(LAYER_ORDER) - set(layers)

    if missing:
        raise ValueError(f"Missing validation layers: {sorted(missing)}")

    statuses = [layers[name]["status"] for name in LAYER_ORDER]

    return {
        "project": "RIDE360",
        "phase": "1",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source": str(source),
        "source_rows": rows,
        "source_columns": columns,
        "status": combined_status(statuses),
        "layers": layers,
        "kpis": kpis,
        "policies": {
            "raw_source_modified": False,
            "automatic_deduplication": False,
            "booking_grain_approved": False,
            "completed_booking_value_provisional": True,
        },
    }


def _read_json(path: Path) -> dict:
    """Read an exported JSON report."""
    return json.loads(path.read_text(encoding="utf-8"))


def run_phase1(
    source: Path,
    output_dir: Path,
) -> dict:
    """Execute profiling and all Phase 1 validation layers."""
    source = Path(source)
    output_dir = Path(output_dir)

    df = load_bookings(source)
    output_dir.mkdir(parents=True, exist_ok=True)

    profiling_dir = output_dir / "profiling"
    structural_dir = output_dir / "structural"
    business_dir = output_dir / "business"
    events_dir = output_dir / "events"
    metadata_dir = output_dir / "metadata"

    export_profile(df, profiling_dir)
    export_quality(df, structural_dir)
    export_business_rules(df, business_dir)
    export_event_rules(df, events_dir)
    export_metadata(df, metadata_dir)

    structural = _read_json(structural_dir / "quality_summary.json")
    business = _read_json(business_dir / "business_summary.json")
    events = _read_json(events_dir / "event_summary.json")
    metadata = _read_json(metadata_dir / "metadata_summary.json")

    layers = {
        "structural": {
            "status": structural["status"],
            "report": "structural/quality_report.html",
        },
        "business": {
            "status": business["status"],
            "report": "business/business_report.html",
        },
        "events": {
            "status": events["status"],
            "report": "events/event_report.html",
        },
        "metadata": {
            "status": metadata["schema"]["status"],
            "report": "metadata/metadata_summary.json",
        },
    }

    manifest = build_manifest(
        source=source,
        rows=len(df),
        columns=len(df.columns),
        layers=layers,
        kpis=metadata["kpis"],
    )

    (output_dir / "phase1_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return manifest


def main() -> int:
    """Command-line entry point for Phase 1 completion."""
    parser = argparse.ArgumentParser(
        description="Run the complete RIDE360 Phase 1 pipeline"
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("data/raw/rideBookings.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/generated/phase1_final"),
    )

    args = parser.parse_args()

    manifest = run_phase1(args.source, args.output)

    print("\nRIDE360 — PHASE 1 FINAL VALIDATION")
    print("-" * 48)
    print(f"Overall status: {manifest['status']}")
    print(f"Source rows: {manifest['source_rows']:,}")
    print(f"Source columns: {manifest['source_columns']}")

    for name, layer in manifest["layers"].items():
        print(f"{name.capitalize()}: {layer['status']}")

    print(f"Reports: {args.output}")
    print("Manifest: phase1_manifest.json")

    return 1 if manifest["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
