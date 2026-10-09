
"""Command-line interface for RIDE360."""

import argparse
import csv
from pathlib import Path

from ride360.profiling import export_profile, load_bookings
from ride360.quality import export_quality

REQUIRED_COLUMNS = {
    "Date",
    "Time",
    "Booking ID",
    "Booking Status",
    "Customer ID",
    "Vehicle Type",
    "Booking Value",
    "Ride Distance",
}


def inspect_csv(path: Path) -> dict[str, object]:
    """Validate CSV headers and count source records."""
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing input CSV: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames or []

        missing = sorted(
            REQUIRED_COLUMNS - set(columns)
        )

        if missing:
            raise ValueError(
                "Missing required columns: "
                + ", ".join(missing)
            )

        count = sum(1 for _ in reader)

    return {
        "path": str(path),
        "rows": count,
        "columns": len(columns),
    }


def main() -> None:
    """Execute the RIDE360 CLI."""
    parser = argparse.ArgumentParser(
        description="RIDE360 Analytics Platform"
    )

    parser.add_argument(
        "command",
        choices=[
            "check-data",
            "profile-data",
            "validate-data",
        ],
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=Path(
            "data/raw/rideBookings.csv"
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
    )

    args = parser.parse_args()

    if args.command == "check-data":
        result = inspect_csv(args.input)

        print("\nRIDE360 DATA VALIDATION")
        print("-" * 40)
        print(
            f"PASS | {result['rows']:,} rows | "
            f"{result['columns']} columns | "
            f"{result['path']}"
        )

    elif args.command == "profile-data":
        output = args.output or Path(
            "reports/generated/phase1"
        )

        df = load_bookings(args.input)
        summary = export_profile(df, output)

        print("\nRIDE360 DATA PROFILING")
        print("-" * 40)
        print(
            f"Total rows: {summary['total_rows']:,}"
        )
        print(
            f"Total columns: {summary['total_columns']}"
        )
        print(
            "Unique booking IDs: "
            f"{summary['unique_booking_ids']:,}"
        )
        print(
            "Missing booking IDs: "
            f"{summary['missing_booking_ids']:,}"
        )
        print(
            "Repeated booking ID rows: "
            f"{summary['repeated_booking_id_rows']:,}"
        )
        print(
            "Extra booking ID occurrences: "
            f"{summary['extra_booking_id_occurrences']:,}"
        )
        print(
            "Exact duplicate rows: "
            f"{summary['duplicate_full_rows']:,}"
        )

        print("\nBooking Status Distribution")

        for status, count in summary[
            "booking_status_counts"
        ].items():
            print(f"  {status}: {count:,}")

        print("\nReports generated successfully.")
        print(f"Output: {output}")

    elif args.command == "validate-data":
        output = args.output or Path(
            "reports/generated/quality"
        )

        df = load_bookings(args.input)
        summary = export_quality(df, output)

        print("\nRIDE360 QUALITY VALIDATION")
        print("-" * 40)
        print(f"Overall status: {summary['status']}")
        print(f"Rows: {summary['rows']:,}")

        if "rules" in summary:
            print(f"Rules evaluated: {summary['rules']}")
            print(f"Error rules: {summary['errors']}")
            print(
                f"Warning rules: {summary['warnings']}"
            )
            print(
                "Repeated ID groups: "
                f"{summary['repeated_id_groups']:,}"
            )
            print(
                "Conflicting ID groups: "
                f"{summary['conflicting_id_groups']:,}"
            )
        else:
            print(
                "Missing columns: "
                + ", ".join(
                    summary.get("missing_columns", [])
                )
            )

        print(f"Reports: {output}")

        if summary["status"] == "FAIL":
            raise SystemExit(1)


if __name__ == "__main__":
    main()
