
"""Tests for conditional cancellation and incomplete-ride rules."""

import json

import pandas as pd
import pytest

from ride360.event_rules import assess_event_rules, export_event_rules


@pytest.fixture
def bookings() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Booking Status": [
                "Completed",
                "Cancelled by Customer",
                "Cancelled by Driver",
                "Incomplete",
                "No Driver Found",
            ],
            "Cancelled Rides by Customer": [
                None, 1, None, None, None
            ],
            "Reason for cancelling by Customer": [
                None, "Change of plans", None, None, None
            ],
            "Cancelled Rides by Driver": [
                None, None, 1, None, None
            ],
            "Driver Cancellation Reason": [
                None, None, "Customer related issue", None, None
            ],
            "Incomplete Rides": [
                None, None, None, 1, None
            ],
            "Incomplete Rides Reason": [
                None, None, None, "Vehicle Breakdown", None
            ],
        }
    )


def count_for(rules: pd.DataFrame, rule_id: str) -> int:
    return int(
        rules.loc[
            rules["rule_id"].eq(rule_id),
            "affected_rows",
        ].iloc[0]
    )


def test_valid_events_pass(bookings: pd.DataFrame) -> None:
    rules, summary = assess_event_rules(bookings)

    assert summary["status"] == "PASS"
    assert summary["rules_evaluated"] == 12
    assert summary["warning_rules"] == 0
    assert len(rules) == 12


@pytest.mark.parametrize(
    ("row", "column", "rule_id"),
    [
        (1, "Cancelled Rides by Customer", "EV001"),
        (1, "Reason for cancelling by Customer", "EV002"),
        (2, "Cancelled Rides by Driver", "EV005"),
        (2, "Driver Cancellation Reason", "EV006"),
        (3, "Incomplete Rides", "EV009"),
        (3, "Incomplete Rides Reason", "EV010"),
    ],
)
def test_missing_expected_field_warns(
    bookings: pd.DataFrame,
    row: int,
    column: str,
    rule_id: str,
) -> None:
    bookings.loc[row, column] = None

    rules, summary = assess_event_rules(bookings)

    assert summary["status"] == "WARN"
    assert count_for(rules, rule_id) == 1


@pytest.mark.parametrize(
    ("column", "value", "rule_id"),
    [
        ("Cancelled Rides by Customer", 1, "EV003"),
        (
            "Reason for cancelling by Customer",
            "Wrong Address",
            "EV004",
        ),
        ("Cancelled Rides by Driver", 1, "EV007"),
        (
            "Driver Cancellation Reason",
            "Personal issue",
            "EV008",
        ),
        ("Incomplete Rides", 1, "EV011"),
        (
            "Incomplete Rides Reason",
            "Other Issue",
            "EV012",
        ),
    ],
)
def test_unexpected_field_warns(
    bookings: pd.DataFrame,
    column: str,
    value: str | int | None,
    rule_id: str,
) -> None:
    bookings.loc[0, column] = value

    rules, summary = assess_event_rules(bookings)

    assert summary["status"] == "WARN"
    assert count_for(rules, rule_id) == 1


def test_invalid_flag_warns(bookings: pd.DataFrame) -> None:
    bookings.loc[1, "Cancelled Rides by Customer"] = 2

    rules, _ = assess_event_rules(bookings)

    assert count_for(rules, "EV001") == 1


def test_blank_reason_warns(bookings: pd.DataFrame) -> None:
    bookings.loc[3, "Incomplete Rides Reason"] = "   "

    rules, _ = assess_event_rules(bookings)

    assert count_for(rules, "EV010") == 1


def test_missing_column_raises(bookings: pd.DataFrame) -> None:
    bookings = bookings.drop(
        columns=["Driver Cancellation Reason"]
    )

    with pytest.raises(
        ValueError,
        match="Missing required columns",
    ):
        assess_event_rules(bookings)


def test_does_not_mutate_source(bookings: pd.DataFrame) -> None:
    original = bookings.copy(deep=True)

    assess_event_rules(bookings)

    pd.testing.assert_frame_equal(bookings, original)


def test_empty_dataset(bookings: pd.DataFrame) -> None:
    rules, summary = assess_event_rules(bookings.iloc[:0])

    assert len(rules) == 12
    assert summary["total_rows"] == 0
    assert summary["status"] == "PASS"


def test_export_reports(
    bookings: pd.DataFrame,
    tmp_path,
) -> None:
    summary = export_event_rules(bookings, tmp_path)

    assert summary["status"] == "PASS"

    for filename in (
        "event_rules.csv",
        "event_summary.json",
        "event_report.html",
    ):
        assert (tmp_path / filename).is_file()

    saved = json.loads(
        (tmp_path / "event_summary.json").read_text(
            encoding="utf-8"
        )
    )

    assert saved["rules_evaluated"] == 12

    html_report = (
        tmp_path / "event_report.html"
    ).read_text(encoding="utf-8")

    assert "EV001" in html_report
    assert "RIDE360" in html_report
