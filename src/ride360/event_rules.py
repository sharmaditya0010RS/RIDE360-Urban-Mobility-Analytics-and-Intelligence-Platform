
"""Conditional event-field validation for RIDE360 bookings.

Checks customer cancellations, driver cancellations, and incomplete
rides without modifying the source DataFrame.
"""

import html
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pandas as pd

EVENT_CONFIG = (
    (
        "Customer cancellation",
        "Cancelled by Customer",
        "Cancelled Rides by Customer",
        "Reason for cancelling by Customer",
        "EV001",
    ),
    (
        "Driver cancellation",
        "Cancelled by Driver",
        "Cancelled Rides by Driver",
        "Driver Cancellation Reason",
        "EV005",
    ),
    (
        "Incomplete ride",
        "Incomplete",
        "Incomplete Rides",
        "Incomplete Rides Reason",
        "EV009",
    ),
)

RESULT_COLUMNS = [
    "rule_id",
    "event",
    "check",
    "severity",
    "result",
    "affected_rows",
    "affected_pct",
    "description",
]


def _present(series: pd.Series) -> pd.Series:
    """Treat null, empty, and whitespace-only text as absent."""
    return series.notna() & series.astype("string").str.strip().ne("").fillna(False)


def _valid_flag(series: pd.Series) -> pd.Series:
    """Recognize numeric one, including 1.0 and string '1'."""
    numeric = pd.to_numeric(series, errors="coerce")
    return numeric.eq(1)


def _record(
    results: list[dict],
    *,
    rule_id: str,
    event: str,
    check: str,
    mask: pd.Series,
    description: str,
    total_rows: int,
) -> None:
    affected = int(mask.fillna(False).sum())
    results.append(
        {
            "rule_id": rule_id,
            "event": event,
            "check": check,
            "severity": "WARN",
            "result": "WARN" if affected else "PASS",
            "affected_rows": affected,
            "affected_pct": (
                round(affected / total_rows * 100, 2)
                if total_rows
                else 0.0
            ),
            "description": description,
        }
    )


def assess_event_rules(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, dict]:
    """Validate event-specific flags and reasons."""
    required = {"Booking Status"}

    for _, _, flag_column, reason_column, _ in EVENT_CONFIG:
        required.update((flag_column, reason_column))

    missing = sorted(required - set(df.columns))

    if missing:
        raise ValueError(
            "Missing required columns: " + ", ".join(missing)
        )

    results: list[dict] = []
    total_rows = len(df)
    status = df["Booking Status"]

    for event, expected_status, flag_column, reason_column, prefix in EVENT_CONFIG:
        expected = status.eq(expected_status).fillna(False)
        unexpected = ~expected

        flag = df[flag_column]
        reason = df[reason_column]

        flag_present = _present(flag)
        reason_present = _present(reason)
        flag_valid = _valid_flag(flag)

        start = int(prefix[-3:])

        _record(
            results,
            rule_id=f"EV{start:03d}",
            event=event,
            check="required_flag",
            mask=expected & ~flag_valid,
            description=(
                f"{expected_status} must have {flag_column} = 1"
            ),
            total_rows=total_rows,
        )

        _record(
            results,
            rule_id=f"EV{start + 1:03d}",
            event=event,
            check="required_reason",
            mask=expected & ~reason_present,
            description=(
                f"{expected_status} must have a nonblank "
                f"{reason_column}"
            ),
            total_rows=total_rows,
        )

        _record(
            results,
            rule_id=f"EV{start + 2:03d}",
            event=event,
            check="unexpected_flag",
            mask=unexpected & flag_present,
            description=(
                f"{flag_column} must be absent outside "
                f"{expected_status}"
            ),
            total_rows=total_rows,
        )

        _record(
            results,
            rule_id=f"EV{start + 3:03d}",
            event=event,
            check="unexpected_reason",
            mask=unexpected & reason_present,
            description=(
                f"{reason_column} must be absent outside "
                f"{expected_status}"
            ),
            total_rows=total_rows,
        )

    rules = pd.DataFrame(results, columns=RESULT_COLUMNS)
    warnings = int(rules["result"].eq("WARN").sum())

    summary = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "status": "WARN" if warnings else "PASS",
        "total_rows": total_rows,
        "rules_evaluated": len(rules),
        "failed_rules": 0,
        "warning_rules": warnings,
        "customer_cancellations": int(
            status.eq("Cancelled by Customer").sum()
        ),
        "driver_cancellations": int(
            status.eq("Cancelled by Driver").sum()
        ),
        "incomplete_rides": int(
            status.eq("Incomplete").sum()
        ),
        "rule_counts": {
            str(row.rule_id): int(cast(int, row.affected_rows))
            for row in rules.itertuples(index=False)
        },
    }

    return rules, summary


def export_event_rules(
    df: pd.DataFrame,
    output_dir: Path,
) -> dict:
    """Write CSV, JSON, and HTML event-validation reports."""
    rules, summary = assess_event_rules(df)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rules.to_csv(
        output_dir / "event_rules.csv",
        index=False,
    )

    (output_dir / "event_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    headers = "".join(
        f"<th>{html.escape(column)}</th>"
        for column in RESULT_COLUMNS
    )

    rows = []

    for values in rules[RESULT_COLUMNS].itertuples(
        index=False, name=None
    ):
        cells = "".join(
            f"<td>{html.escape(str(value))}</td>"
            for value in values
        )
        rows.append(f"<tr>{cells}</tr>")

    table_rows = "\n".join(rows)

    document = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RIDE360 Event Validation</title>
<style>
body {{
    margin: 0;
    padding: 40px 24px;
    background: #0b1220;
    color: #e5edf8;
    font-family: Arial, sans-serif;
}}
main {{
    max-width: 1200px;
    margin: auto;
}}
h1 {{
    color: #60d6c7;
}}
.summary {{
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    margin: 24px 0;
}}
.metric {{
    background: #182338;
    border-radius: 12px;
    padding: 20px;
    min-width: 150px;
}}
.metric strong {{
    display: block;
    margin-top: 10px;
    font-size: 26px;
}}
.table-wrap {{
    overflow-x: auto;
}}
table {{
    width: 100%;
    border-collapse: collapse;
    background: #182338;
}}
th, td {{
    padding: 12px;
    border-bottom: 1px solid #344158;
    text-align: left;
}}
th {{
    color: #60d6c7;
}}
.note {{
    color: #a8b6c9;
    margin-top: 24px;
}}
</style>
</head>
<body>
<main>
<h1>RIDE360 | Event Validation</h1>
<div class="summary">
<div class="metric">Status<strong>{summary["status"]}</strong></div>
<div class="metric">Rows<strong>{total_format(summary["total_rows"])}</strong></div>
<div class="metric">Rules<strong>{summary["rules_evaluated"]}</strong></div>
<div class="metric">Warnings<strong>{summary["warning_rules"]}</strong></div>
</div>
<div class="table-wrap">
<table>
<thead><tr>{headers}</tr></thead>
<tbody>{table_rows}</tbody>
</table>
</div>
<p class="note">
Warnings indicate event-field inconsistencies requiring review.
The source dataset has not been modified.
</p>
</main>
</body>
</html>
"""

    (output_dir / "event_report.html").write_text(
        document,
        encoding="utf-8",
    )

    return summary


def total_format(value: int) -> str:
    """Format counts for HTML summaries."""
    return f"{value:,}"
