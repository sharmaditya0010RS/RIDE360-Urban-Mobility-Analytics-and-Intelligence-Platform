
"""Command-line entry point and source-file checks."""

import argparse
import csv
from pathlib import Path

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
    """Validate the CSV header and count records."""
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing input CSV: {path}"
        )

    with path.open(
        "r", encoding="utf-8-sig", newline=""
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
    parser = argparse.ArgumentParser(
        description="RIDE360 project tools"
    )

    parser.add_argument(
        "command",
        choices=["check-data"],
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/raw/rideBookings.csv"),
    )

    args = parser.parse_args()

    if args.command == "check-data":
        result = inspect_csv(args.input)
        print(
            f"PASS | {result['rows']:,} rows | "
            f"{result['columns']} columns | "
            f"{result['path']}"
        )


if __name__ == "__main__":
    main()
