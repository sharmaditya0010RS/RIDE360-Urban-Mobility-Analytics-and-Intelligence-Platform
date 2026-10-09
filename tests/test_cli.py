
"""Tests for RIDE360 CLI data validation."""

import csv
from pathlib import Path

import pytest

from ride360.cli import inspect_csv


def test_valid_csv(tmp_path: Path) -> None:
    path = tmp_path / "valid.csv"

    columns = [
        "Date",
        "Time",
        "Booking ID",
        "Booking Status",
        "Customer ID",
        "Vehicle Type",
        "Booking Value",
        "Ride Distance",
    ]

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=columns,
        )

        writer.writeheader()

        writer.writerow({
            key: "sample"
            for key in columns
        })

    result = inspect_csv(path)

    assert result["rows"] == 1
    assert result["columns"] == 8


def test_missing_csv(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        inspect_csv(
            tmp_path / "missing.csv"
        )


def test_missing_columns(
    tmp_path: Path,
) -> None:
    path = tmp_path / "invalid.csv"

    path.write_text(
        "Date,Time\n2024-01-01,12:00\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Missing required columns",
    ):
        inspect_csv(path)
