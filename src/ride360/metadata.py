
"""Versioned source data dictionary and KPI contracts for RIDE360."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd


def _column(
    name: str,
    data_type: str,
    nullable: str,
    description: str,
    analytical_role: str,
) -> dict[str, str]:
    return {
        "column_name": name,
        "logical_type": data_type,
        "null_policy": nullable,
        "description": description,
        "analytical_role": analytical_role,
    }


DATA_DICTIONARY = [
    _column("Date", "date", "required", "Booking date.", "time_dimension"),
    _column("Time", "time", "required", "Booking time.", "time_dimension"),
    _column(
        "Booking ID",
        "string",
        "required",
        "Source booking identifier; uniqueness is not guaranteed.",
        "identifier",
    ),
    _column(
        "Booking Status",
        "category",
        "required",
        "Reported booking outcome.",
        "dimension",
    ),
    _column(
        "Customer ID",
        "string",
        "required",
        "Source customer identifier.",
        "identifier",
    ),
    _column(
        "Vehicle Type",
        "category",
        "review",
        "Requested or assigned vehicle category.",
        "dimension",
    ),
    _column(
        "Pickup Location",
        "string",
        "review",
        "Reported pickup location.",
        "dimension",
    ),
    _column(
        "Drop Location",
        "string",
        "review",
        "Reported destination.",
        "dimension",
    ),
    _column(
        "Avg VTAT",
        "number",
        "conditional",
        "Source average vehicle arrival time; unit needs confirmation.",
        "measure",
    ),
    _column(
        "Avg CTAT",
        "number",
        "conditional",
        "Source average customer arrival time; unit needs confirmation.",
        "measure",
    ),
    _column(
        "Cancelled Rides by Customer",
        "flag",
        "conditional",
        "Equals 1 for customer-cancelled records; otherwise absent.",
        "event_flag",
    ),
    _column(
        "Reason for cancelling by Customer",
        "category",
        "conditional",
        "Reason for customer cancellation.",
        "event_reason",
    ),
    _column(
        "Cancelled Rides by Driver",
        "flag",
        "conditional",
        "Equals 1 for driver-cancelled records; otherwise absent.",
        "event_flag",
    ),
    _column(
        "Driver Cancellation Reason",
        "category",
        "conditional",
        "Reason for driver cancellation.",
        "event_reason",
    ),
    _column(
        "Incomplete Rides",
        "flag",
        "conditional",
        "Equals 1 for incomplete records; otherwise absent.",
        "event_flag",
    ),
    _column(
        "Incomplete Rides Reason",
        "category",
        "conditional",
        "Reason for incomplete ride.",
        "event_reason",
    ),
    _column(
        "Booking Value",
        "number",
        "conditional",
        "Reported booking monetary value; currency unconfirmed.",
        "measure",
    ),
    _column(
        "Ride Distance",
        "number",
        "conditional",
        "Reported ride distance; unit unconfirmed.",
        "measure",
    ),
    _column(
        "Driver Ratings",
        "number",
        "conditional",
        "Reported driver rating, expected range 1 to 5.",
        "measure",
    ),
    _column(
        "Customer Rating",
        "number",
        "conditional",
        "Reported customer rating, expected range 1 to 5.",
        "measure",
    ),
    _column(
        "Payment Method",
        "category",
        "review",
        "Reported payment method; not proof of settlement.",
        "dimension",
    ),
]


KPI_CONTRACTS = [
    {
        "kpi_id": "KPI001",
        "name": "Booking Records",
        "grain": "source_record",
        "unit": "records",
        "numerator": "COUNT(*)",
        "denominator": None,
        "status": "approved",
    },
    {
        "kpi_id": "KPI002",
        "name": "Distinct Booking IDs",
        "grain": "source_identifier",
        "unit": "identifiers",
        "numerator": "COUNT(DISTINCT Booking ID)",
        "denominator": None,
        "status": "approved",
    },
    {
        "kpi_id": "KPI003",
        "name": "Completed Records",
        "grain": "source_record",
        "unit": "records",
        "numerator": "COUNT WHERE Booking Status = Completed",
        "denominator": None,
        "status": "approved",
    },
    {
        "kpi_id": "KPI004",
        "name": "Completion Rate",
        "grain": "source_record",
        "unit": "percentage",
        "numerator": "Completed Records",
        "denominator": "Booking Records",
        "status": "approved",
    },
    {
        "kpi_id": "KPI005",
        "name": "Customer Cancellation Rate",
        "grain": "source_record",
        "unit": "percentage",
        "numerator": "COUNT WHERE Booking Status = Cancelled by Customer",
        "denominator": "Booking Records",
        "status": "approved",
    },
    {
        "kpi_id": "KPI006",
        "name": "Driver Cancellation Rate",
        "grain": "source_record",
        "unit": "percentage",
        "numerator": "COUNT WHERE Booking Status = Cancelled by Driver",
        "denominator": "Booking Records",
        "status": "approved",
    },
    {
        "kpi_id": "KPI007",
        "name": "Overall Cancellation Rate",
        "grain": "source_record",
        "unit": "percentage",
        "numerator": "Customer Cancelled + Driver Cancelled",
        "denominator": "Booking Records",
        "status": "approved",
    },
    {
        "kpi_id": "KPI008",
        "name": "Incomplete Rate",
        "grain": "source_record",
        "unit": "percentage",
        "numerator": "COUNT WHERE Booking Status = Incomplete",
        "denominator": "Booking Records",
        "status": "approved",
    },
    {
        "kpi_id": "KPI009",
        "name": "No Driver Found Rate",
        "grain": "source_record",
        "unit": "percentage",
        "numerator": "COUNT WHERE Booking Status = No Driver Found",
        "denominator": "Booking Records",
        "status": "approved",
    },
    {
        "kpi_id": "KPI010",
        "name": "Completed Booking Value",
        "grain": "source_record",
        "unit": "source_currency_unconfirmed",
        "numerator": "SUM Booking Value WHERE Booking Status = Completed",
        "denominator": None,
        "status": "provisional",
    },
]


REQUIRED_KPI_COLUMNS = {
    "Booking ID",
    "Booking Status",
    "Booking Value",
}


def validate_metadata() -> None:
    """Fail when dictionary or contract definitions are inconsistent."""
    names = [item["column_name"] for item in DATA_DICTIONARY]
    ids = [item["kpi_id"] for item in KPI_CONTRACTS]

    if len(names) != 21 or len(names) != len(set(names)):
        raise ValueError("Expected exactly 21 unique source columns")

    if len(ids) != len(set(ids)):
        raise ValueError("KPI IDs must be unique")

    if not REQUIRED_KPI_COLUMNS.issubset(names):
        raise ValueError("KPI source columns missing from dictionary")


def validate_source_schema(df: pd.DataFrame) -> dict:
    """Compare observed columns against the versioned dictionary."""
    validate_metadata()

    expected = {item["column_name"] for item in DATA_DICTIONARY}
    actual = set(df.columns)

    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)

    return {
        "status": "PASS" if not missing and not unexpected else "FAIL",
        "expected_columns": len(expected),
        "observed_columns": len(df.columns),
        "missing_columns": missing,
        "unexpected_columns": unexpected,
    }


def calculate_record_kpis(df: pd.DataFrame) -> dict:
    """Calculate approved record-grain metrics without deduplication."""
    missing = sorted(REQUIRED_KPI_COLUMNS - set(df.columns))

    if missing:
        raise ValueError("Missing KPI columns: " + ", ".join(missing))

    status = df["Booking Status"]
    total = len(df)

    counts = {
        "completed_records": int(status.eq("Completed").sum()),
        "customer_cancelled_records": int(
            status.eq("Cancelled by Customer").sum()
        ),
        "driver_cancelled_records": int(
            status.eq("Cancelled by Driver").sum()
        ),
        "incomplete_records": int(status.eq("Incomplete").sum()),
        "no_driver_found_records": int(
            status.eq("No Driver Found").sum()
        ),
    }

    def rate(count: int) -> float | None:
        return round(count / total * 100, 4) if total else None

    completed_value = pd.to_numeric(
        df.loc[status.eq("Completed"), "Booking Value"],
        errors="coerce",
    )

    result = {
        "booking_records": total,
        "distinct_booking_ids": int(df["Booking ID"].nunique(dropna=True)),
        **counts,
        "completion_rate_pct": rate(counts["completed_records"]),
        "customer_cancellation_rate_pct": rate(
            counts["customer_cancelled_records"]
        ),
        "driver_cancellation_rate_pct": rate(
            counts["driver_cancelled_records"]
        ),
        "overall_cancellation_rate_pct": rate(
            counts["customer_cancelled_records"]
            + counts["driver_cancelled_records"]
        ),
        "incomplete_rate_pct": rate(counts["incomplete_records"]),
        "no_driver_found_rate_pct": rate(
            counts["no_driver_found_records"]
        ),
        "completed_booking_value": (
            float(completed_value.sum(min_count=1))
            if completed_value.notna().any()
            else None
        ),
        "completed_booking_value_status": "provisional",
    }

    return result


def export_metadata(df: pd.DataFrame, output_dir: Path) -> dict:
    """Export dictionary, contracts, schema assessment and KPI snapshot."""
    validate_metadata()

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    dictionary = pd.DataFrame(DATA_DICTIONARY)
    contracts = pd.DataFrame(KPI_CONTRACTS)

    dictionary.to_csv(
        output_dir / "data_dictionary.csv",
        index=False,
    )
    contracts.to_csv(
        output_dir / "kpi_contracts.csv",
        index=False,
    )

    schema = validate_source_schema(df)
    kpis = calculate_record_kpis(df)

    summary = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "schema": schema,
        "kpis": kpis,
        "dictionary_columns": len(dictionary),
        "kpi_contracts": len(contracts),
    }

    (output_dir / "metadata_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return summary
