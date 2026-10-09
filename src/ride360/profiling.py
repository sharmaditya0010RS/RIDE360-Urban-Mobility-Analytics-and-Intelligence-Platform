
"""Reusable source-data profiling for RIDE360."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd


def load_bookings(path: Path) -> pd.DataFrame:
    """Load bookings without modifying the raw source."""
    if not path.is_file():
        raise FileNotFoundError(
            f"CSV not found: {path}"
        )

    df = pd.read_csv(
        path,
        low_memory=False,
        encoding="utf-8-sig",
    )

    if df.empty:
        raise ValueError(
            "Source CSV contains no records"
        )

    if df.columns.duplicated().any():
        raise ValueError(
            "Duplicate column names detected"
        )

    return df


def profile_columns(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate completeness and uniqueness statistics."""
    records = []
    total = len(df)

    for column in df.columns:
        series = df[column]

        missing = int(series.isna().sum())
        unique = int(
            series.nunique(dropna=True)
        )

        non_null = total - missing

        records.append({
            "column": column,
            "dtype": str(series.dtype),
            "total_rows": total,
            "non_null_count": non_null,
            "missing_count": missing,
            "missing_pct": round(
                100 * missing / total, 2
            ) if total else 0,
            "unique_count": unique,
            "unique_pct": round(
                100 * unique / total, 2
            ) if total else 0,
            "sample_value": (
                str(series.dropna().iloc[0])
                if series.notna().any()
                else None
            ),
        })

    return pd.DataFrame(records)


def profile_numeric(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate descriptive statistics for numeric data."""
    numeric = df.select_dtypes(
        include="number"
    )

    columns = [
        "column",
        "count",
        "mean",
        "median",
        "std",
        "min",
        "max",
    ]

    records = []

    for column in numeric.columns:
        series = numeric[column]

        records.append({
            "column": column,
            "count": int(series.count()),
            "mean": series.mean(),
            "median": series.median(),
            "std": series.std(),
            "min": series.min(),
            "max": series.max(),
        })

    return pd.DataFrame(
        records,
        columns=columns,
    )


def profile_bookings(
    df: pd.DataFrame,
) -> dict:
    """Calculate dataset-level quality metrics."""
    required = {
        "Booking ID",
        "Booking Status",
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    booking_ids = df["Booking ID"]

    repeated_mask = (
        booking_ids.notna()
        & booking_ids.duplicated(
            keep=False
        )
    )

    status_counts = (
        df["Booking Status"]
        .fillna("<MISSING>")
        .astype(str)
        .value_counts()
    )

    return {
        "generated_at_utc": datetime.now(
            UTC
        ).isoformat(),
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "duplicate_full_rows": int(
            df.duplicated().sum()
        ),
        "unique_booking_ids": int(
            booking_ids.nunique(
                dropna=True
            )
        ),
        "missing_booking_ids": int(
            booking_ids.isna().sum()
        ),
        "repeated_booking_id_rows": int(
            repeated_mask.sum()
        ),
        "extra_booking_id_occurrences": int(
            booking_ids.dropna()
            .duplicated()
            .sum()
        ),
        "booking_status_counts": {
            str(key): int(value)
            for key, value in status_counts.items()
        },
    }


def export_profile(
    df: pd.DataFrame,
    output_dir: Path,
) -> dict:
    """Export profiling reports to CSV and JSON."""
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    summary = profile_bookings(df)

    column_report = profile_columns(df)
    numeric_report = profile_numeric(df)

    duplicate_mask = (
        df["Booking ID"].notna()
        & df["Booking ID"].duplicated(
            keep=False
        )
    )

    duplicate_report = (
        df.loc[duplicate_mask]
        .sort_values("Booking ID")
    )

    column_report.to_csv(
        output_dir / "column_profile.csv",
        index=False,
    )

    numeric_report.to_csv(
        output_dir / "numeric_profile.csv",
        index=False,
    )

    duplicate_report.to_csv(
        output_dir / "duplicate_booking_ids.csv",
        index=False,
    )

    with (
        output_dir / "source_summary.json"
    ).open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            summary,
            file,
            indent=2,
            ensure_ascii=False,
        )

    return summary
