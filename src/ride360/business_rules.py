
"""Business-level consistency checks for RIDE360 bookings.

Rules are observational and non-destructive. They do not
modify, deduplicate, or delete source booking records.
"""

import html
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = [
    "Booking ID",
    "Booking Status",
    "Booking Value",
    "Ride Distance",
    "Driver Ratings",
    "Customer Rating",
]

COMPLETED = "Completed"

CANCELLED_STATUSES = {
    "Cancelled by Driver",
    "Cancelled by Customer",
}

NON_COMPLETED_STATUSES = {
    "Cancelled by Driver",
    "Cancelled by Customer",
    "No Driver Found",
    "Incomplete",
}

REPORT_COLUMNS = [
    "rule_id",
    "category",
    "severity",
    "result",
    "affected_rows",
    "affected_pct",
    "description",
]


def _add_rule(
    records: list[dict],
    *,
    rule_id: str,
    category: str,
    severity: str,
    mask: pd.Series,
    description: str,
    total_rows: int,
) -> None:
    """Append a standardized quality-rule result."""
    affected = int(mask.fillna(False).sum())

    if affected == 0:
        result = "PASS"
    elif severity == "ERROR":
        result = "FAIL"
    elif severity == "WARN":
        result = "WARN"
    else:
        result = "INFO"

    records.append({
        "rule_id": rule_id,
        "category": category,
        "severity": severity,
        "result": result,
        "affected_rows": affected,
        "affected_pct": round(
            100 * affected / total_rows, 2
        ) if total_rows else 0.0,
        "description": description,
    })


def assess_business_rules(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, dict]:
    """Evaluate booking business rules and return results."""
    missing = sorted(
        set(REQUIRED_COLUMNS) - set(df.columns)
    )

    if missing:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(missing)
        )

    total_rows = len(df)
    records: list[dict] = []

    status = df["Booking Status"]

    completed = status.eq(COMPLETED)
    cancelled = status.isin(CANCELLED_STATUSES)
    non_completed = status.isin(
        NON_COMPLETED_STATUSES
    )

    booking_value = pd.to_numeric(
        df["Booking Value"],
        errors="coerce",
    )

    ride_distance = pd.to_numeric(
        df["Ride Distance"],
        errors="coerce",
    )

    driver_rating = pd.to_numeric(
        df["Driver Ratings"],
        errors="coerce",
    )

    customer_rating = pd.to_numeric(
        df["Customer Rating"],
        errors="coerce",
    )

    _add_rule(
        records,
        rule_id="BR001",
        category="Completeness",
        severity="WARN",
        mask=completed & booking_value.isna(),
        description=(
            "Completed booking has missing or "
            "non-numeric booking value"
        ),
        total_rows=total_rows,
    )

    _add_rule(
        records,
        rule_id="BR002",
        category="Completeness",
        severity="WARN",
        mask=completed & ride_distance.isna(),
        description=(
            "Completed booking has missing or "
            "non-numeric ride distance"
        ),
        total_rows=total_rows,
    )

    _add_rule(
        records,
        rule_id="BR003",
        category="Value consistency",
        severity="WARN",
        mask=completed & booking_value.le(0),
        description=(
            "Completed booking has zero or "
            "negative booking value"
        ),
        total_rows=total_rows,
    )

    _add_rule(
        records,
        rule_id="BR004",
        category="Distance consistency",
        severity="WARN",
        mask=completed & ride_distance.le(0),
        description=(
            "Completed booking has zero or "
            "negative ride distance"
        ),
        total_rows=total_rows,
    )

    _add_rule(
        records,
        rule_id="BR005",
        category="Rating completeness",
        severity="INFO",
        mask=completed & driver_rating.isna(),
        description=(
            "Completed booking has no usable "
            "driver rating"
        ),
        total_rows=total_rows,
    )

    _add_rule(
        records,
        rule_id="BR006",
        category="Rating completeness",
        severity="INFO",
        mask=completed & customer_rating.isna(),
        description=(
            "Completed booking has no usable "
            "customer rating"
        ),
        total_rows=total_rows,
    )

    _add_rule(
        records,
        rule_id="BR007",
        category="Rating consistency",
        severity="WARN",
        mask=non_completed & driver_rating.notna(),
        description=(
            "Non-completed booking contains "
            "a driver rating; review semantics"
        ),
        total_rows=total_rows,
    )

    _add_rule(
        records,
        rule_id="BR008",
        category="Rating consistency",
        severity="WARN",
        mask=non_completed & customer_rating.notna(),
        description=(
            "Non-completed booking contains "
            "a customer rating; review semantics"
        ),
        total_rows=total_rows,
    )

    _add_rule(
        records,
        rule_id="BR009",
        category="Cancellation",
        severity="INFO",
        mask=cancelled,
        description=(
            "Cancelled bookings; cancellation "
            "reason review is handled separately"
        ),
        total_rows=total_rows,
    )

    rules = pd.DataFrame(
        records,
        columns=REPORT_COLUMNS,
    )

    fail_count = int(
        rules["result"].eq("FAIL").sum()
    )

    warn_count = int(
        rules["result"].eq("WARN").sum()
    )

    info_count = int(
        rules["result"].eq("INFO").sum()
    )

    overall = (
        "FAIL"
        if fail_count
        else "WARN"
        if warn_count
        else "PASS"
    )

    summary = {
        "generated_at_utc": datetime.now(
            UTC
        ).isoformat(),
        "status": overall,
        "total_rows": total_rows,
        "rules_evaluated": len(rules),
        "failed_rules": fail_count,
        "warning_rules": warn_count,
        "informational_rules": info_count,
        "completed_rows": int(completed.sum()),
        "cancelled_rows": int(cancelled.sum()),
        "non_completed_rows": int(
            non_completed.sum()
        ),
        "rule_counts": {
            str(rule["rule_id"]): int(
                rule["affected_rows"]
            )
            for rule in rules[
                ["rule_id", "affected_rows"]
            ].to_dict(orient="records")
        },
    }

    return rules, summary


def export_business_rules(
    df: pd.DataFrame,
    output_dir: Path,
) -> dict:
    """Save business rule results as CSV, JSON and HTML."""
    rules, summary = assess_business_rules(df)

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    rules.to_csv(
        output_dir / "business_rules.csv",
        index=False,
    )

    (
        output_dir / "business_summary.json"
    ).write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    columns = [
        "rule_id",
        "category",
        "severity",
        "result",
        "affected_rows",
        "affected_pct",
        "description",
    ]

    header = "".join(
        f"<th>{html.escape(column)}</th>"
        for column in columns
    )

    body_rows = []

    for values in rules[
        columns
    ].itertuples(index=False, name=None):
        cells = "".join(
            "<td>"
            + html.escape(str(value))
            + "</td>"
            for value in values
        )

        body_rows.append(
            f"<tr>{cells}</tr>"
        )

    table_body = "\n".join(body_rows)

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport"
      content="width=device-width, initial-scale=1">
<title>RIDE360 | Business Rule Report</title>
<style>
:root {{
    color-scheme: dark;
}}
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
.subtitle {{
    color: #a8b6c9;
}}
.cards {{
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    margin: 28px 0;
}}
.card {{
    background: #182338;
    padding: 22px;
    border-radius: 12px;
    min-width: 150px;
}}
.card strong {{
    display: block;
    margin-top: 10px;
    font-size: 28px;
}}
table {{
    width: 100%;
    border-collapse: collapse;
    background: #182338;
}}
th, td {{
    padding: 14px;
    border-bottom: 1px solid #344158;
    text-align: left;
}}
th {{
    color: #60d6c7;
}}
.table-wrap {{
    overflow-x: auto;
}}
footer {{
    margin-top: 24px;
    color: #a8b6c9;
}}
</style>
</head>
<body>
<main>
<h1>RIDE360 | Business Rule Validation</h1>
<p class="subtitle">
Non-destructive booking consistency assessment
</p>

<div class="cards">
<div class="card">
Status
<strong>{summary["status"]}</strong>
</div>
<div class="card">
Source Rows
<strong>{summary["total_rows"]:,}</strong>
</div>
<div class="card">
Warning Rules
<strong>{summary["warning_rules"]}</strong>
</div>
<div class="card">
Failed Rules
<strong>{summary["failed_rules"]}</strong>
</div>
</div>

<div class="table-wrap">
<table>
<thead><tr>{header}</tr></thead>
<tbody>{table_body}</tbody>
</table>
</div>

<footer>
These rules are preliminary business assumptions.
No source records have been changed or deleted.
</footer>
</main>
</body>
</html>
"""

    (
        output_dir / "business_report.html"
    ).write_text(
        page,
        encoding="utf-8",
    )

    return summary
