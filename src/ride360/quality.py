
"""Non-destructive booking data quality checks and reporting."""

import html
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

REQUIRED = [
    "Date",
    "Time",
    "Booking ID",
    "Booking Status",
    "Customer ID",
    "Vehicle Type",
    "Pickup Location",
    "Drop Location",
    "Booking Value",
    "Ride Distance",
    "Driver Ratings",
    "Customer Rating",
]

STATUSES = {
    "Completed",
    "Cancelled by Driver",
    "Cancelled by Customer",
    "No Driver Found",
    "Incomplete",
}


def assess_quality(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Return quality rules, duplicate conflicts and summary."""
    n = len(df)
    checks = []

    def add(
        rule: str,
        severity: str,
        failures: int,
        detail: str,
    ) -> None:
        checks.append({
            "rule": rule,
            "severity": severity,
            "failed_rows": int(failures),
            "failure_pct": round(
                100 * failures / n, 2
            ) if n else 0.0,
            "result": (
                "PASS" if failures == 0
                else "FAIL" if severity == "ERROR"
                else "WARN"
            ),
            "detail": detail,
        })

    missing = sorted(
        set(REQUIRED) - set(df.columns)
    )

    add(
        "required_columns",
        "ERROR",
        len(missing),
        ", ".join(missing) or "All present",
    )

    if missing:
        results = pd.DataFrame(checks)
        return results, pd.DataFrame(), {
            "status": "FAIL",
            "rows": n,
            "missing_columns": missing,
        }

    for col in [
        "Booking ID",
        "Customer ID",
        "Date",
        "Time",
        "Booking Status",
    ]:
        add(
            f"non_null:{col}",
            "ERROR",
            df[col].isna().sum(),
            "Mandatory field",
        )

    add(
        "known_booking_status",
        "ERROR",
        (~df["Booking Status"].isin(STATUSES)).sum(),
        "Approved status vocabulary",
    )

    parsed_dates = pd.to_datetime(
        df["Date"],
        errors="coerce",
        format="%Y-%m-%d",
    )

    add(
        "valid_date",
        "ERROR",
        parsed_dates.isna().sum(),
        "ISO YYYY-MM-DD",
    )

    parsed_times = pd.to_datetime(
        df["Time"],
        errors="coerce",
        format="%H:%M:%S",
    )

    add(
        "valid_time",
        "ERROR",
        parsed_times.isna().sum(),
        "HH:MM:SS",
    )

    for col in [
        "Booking Value",
        "Ride Distance",
    ]:
        values = pd.to_numeric(
            df[col],
            errors="coerce",
        )

        invalid = (
            df[col].notna()
            & (
                values.isna()
                | (values < 0)
            )
        )

        add(
            f"nonnegative_numeric:{col}",
            "ERROR",
            invalid.sum(),
            "Null allowed; non-null must be nonnegative",
        )

    for col in [
        "Driver Ratings",
        "Customer Rating",
    ]:
        values = pd.to_numeric(
            df[col],
            errors="coerce",
        )

        invalid = (
            df[col].notna()
            & (
                values.isna()
                | ~values.between(1, 5)
            )
        )

        add(
            f"rating_range:{col}",
            "ERROR",
            invalid.sum(),
            "Null allowed; ratings must be 1-5",
        )

    repeated = (
        df["Booking ID"].notna()
        & df["Booking ID"].duplicated(
            keep=False
        )
    )

    add(
        "unique_booking_id",
        "WARN",
        repeated.sum(),
        "Review IDs; no automatic deletion",
    )

    conflicts = []

    for booking_id, group in (
        df.loc[repeated]
        .groupby("Booking ID", sort=False)
    ):
        changing = [
            col
            for col in [
                "Date",
                "Time",
                "Booking Status",
                "Customer ID",
                "Booking Value",
            ]
            if group[col].nunique(
                dropna=False
            ) > 1
        ]

        conflicts.append({
            "booking_id": booking_id,
            "row_count": len(group),
            "different_fields": ", ".join(changing),
            "has_conflict": bool(changing),
        })

    conflict_df = pd.DataFrame(
        conflicts,
        columns=[
            "booking_id",
            "row_count",
            "different_fields",
            "has_conflict",
        ],
    )

    results = pd.DataFrame(checks)

    status = (
        "FAIL"
        if (results["result"] == "FAIL").any()
        else "WARN"
        if (results["result"] == "WARN").any()
        else "PASS"
    )

    summary = {
        "generated_at_utc": datetime.now(
            UTC
        ).isoformat(),
        "status": status,
        "rows": n,
        "rules": len(results),
        "errors": int(
            (results["result"] == "FAIL").sum()
        ),
        "warnings": int(
            (results["result"] == "WARN").sum()
        ),
        "repeated_id_groups": len(conflict_df),
        "conflicting_id_groups": (
            int(conflict_df["has_conflict"].sum())
            if len(conflict_df)
            else 0
        ),
    }

    return results, conflict_df, summary


def export_quality(
    df: pd.DataFrame,
    output_dir: Path,
) -> dict:
    """Export quality results to CSV, JSON and HTML."""
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    rules, conflicts, summary = assess_quality(df)

    rules.to_csv(
        output_dir / "quality_rules.csv",
        index=False,
    )

    conflicts.to_csv(
        output_dir / "duplicate_conflicts.csv",
        index=False,
    )

    (
        output_dir / "quality_summary.json"
    ).write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    rows = "".join(
        "<tr>"
        + "".join(
            f"<td>{html.escape(str(value))}</td>"
            for value in row
        )
        + "</tr>"
        for row in rules[
            [
                "rule",
                "severity",
                "failed_rows",
                "result",
                "detail",
            ]
        ].itertuples(index=False, name=None)
    )

    page = (
        "<!doctype html>"
        "<html lang='en'>"
        "<meta charset='utf-8'>"
        "<meta name='viewport' "
        "content='width=device-width,initial-scale=1'>"
        "<title>RIDE360 Quality Report</title>"
        "<style>"
        "body{font:16px system-ui;"
        "background:#0b1220;color:#e5edf8;"
        "max-width:1100px;margin:48px auto;padding:20px}"
        "h1{color:#60d6c7}"
        "table{border-collapse:collapse;width:100%;"
        "background:#182338}"
        "td,th{padding:12px;"
        "border-bottom:1px solid #344158;"
        "text-align:left}"
        "th{color:#60d6c7}"
        "</style>"
        "<h1>RIDE360 | Data Quality</h1>"
        f"<p>Overall: <strong>{summary['status']}</strong>"
        f" | Rows: {summary['rows']:,}"
        f" | Errors: {summary['errors']}"
        f" | Warnings: {summary['warnings']}</p>"
        "<table><thead><tr>"
        "<th>Rule</th><th>Severity</th>"
        "<th>Failed rows</th><th>Result</th>"
        "<th>Detail</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></html>"
    )

    (
        output_dir / "quality_report.html"
    ).write_text(
        page,
        encoding="utf-8",
    )

    return summary
