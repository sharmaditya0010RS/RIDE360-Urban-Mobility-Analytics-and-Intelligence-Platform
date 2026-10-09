
"""Unit tests for RIDE360 business rules."""

import json

import pandas as pd
import pytest

from ride360.business_rules import (
    assess_business_rules,
    export_business_rules,
)


@pytest.fixture
def sample_data() -> pd.DataFrame:
    """Create a minimal valid booking sample."""
    return pd.DataFrame({
        "Booking ID": [
            "B001",
            "B002",
            "B003",
        ],
        "Booking Status": [
            "Completed",
            "Cancelled by Driver",
            "No Driver Found",
        ],
        "Booking Value": [
            250.0,
            None,
            None,
        ],
        "Ride Distance": [
            5.0,
            None,
            None,
        ],
        "Driver Ratings": [
            4.5,
            None,
            None,
        ],
        "Customer Rating": [
            4.0,
            None,
            None,
        ],
    })


def get_rule(
    rules: pd.DataFrame,
    rule_id: str,
) -> pd.Series:
    """Find one business rule by its stable ID."""
    return rules.loc[
        rules["rule_id"].eq(rule_id)
    ].iloc[0]


def test_valid_sample_passes(
    sample_data: pd.DataFrame,
) -> None:
    rules, summary = assess_business_rules(
        sample_data
    )

    assert summary["status"] == "PASS"
    assert summary["failed_rules"] == 0
    assert summary["warning_rules"] == 0
    assert len(rules) == 9


def test_completed_missing_value_warns(
    sample_data: pd.DataFrame,
) -> None:
    sample_data.loc[
        0, "Booking Value"
    ] = None

    rules, summary = assess_business_rules(
        sample_data
    )

    assert summary["status"] == "WARN"

    rule = get_rule(rules, "BR001")

    assert rule["result"] == "WARN"
    assert rule["affected_rows"] == 1


def test_completed_missing_distance_warns(
    sample_data: pd.DataFrame,
) -> None:
    sample_data.loc[
        0, "Ride Distance"
    ] = None

    rules, _ = assess_business_rules(
        sample_data
    )

    assert get_rule(
        rules, "BR002"
    )["affected_rows"] == 1


def test_zero_booking_value_warns(
    sample_data: pd.DataFrame,
) -> None:
    sample_data.loc[
        0, "Booking Value"
    ] = 0

    rules, _ = assess_business_rules(
        sample_data
    )

    assert get_rule(
        rules, "BR003"
    )["affected_rows"] == 1


def test_zero_distance_warns(
    sample_data: pd.DataFrame,
) -> None:
    sample_data.loc[
        0, "Ride Distance"
    ] = 0

    rules, _ = assess_business_rules(
        sample_data
    )

    assert get_rule(
        rules, "BR004"
    )["affected_rows"] == 1


def test_missing_rating_is_informational(
    sample_data: pd.DataFrame,
) -> None:
    sample_data.loc[
        0, "Driver Ratings"
    ] = None

    rules, summary = assess_business_rules(
        sample_data
    )

    assert summary["status"] == "PASS"

    rule = get_rule(rules, "BR005")

    assert rule["result"] == "INFO"
    assert rule["affected_rows"] == 1


def test_non_completed_rating_warns(
    sample_data: pd.DataFrame,
) -> None:
    sample_data.loc[
        1, "Driver Ratings"
    ] = 4.5

    rules, summary = assess_business_rules(
        sample_data
    )

    assert summary["status"] == "WARN"

    assert get_rule(
        rules, "BR007"
    )["affected_rows"] == 1


def test_missing_required_column_raises(
    sample_data: pd.DataFrame,
) -> None:
    invalid = sample_data.drop(
        columns=["Booking ID"]
    )

    with pytest.raises(
        ValueError,
        match="Missing required columns",
    ):
        assess_business_rules(invalid)


def test_source_is_not_modified(
    sample_data: pd.DataFrame,
) -> None:
    original = sample_data.copy(deep=True)

    assess_business_rules(sample_data)

    pd.testing.assert_frame_equal(
        sample_data,
        original,
    )


def test_export_business_reports(
    sample_data: pd.DataFrame,
    tmp_path,
) -> None:
    summary = export_business_rules(
        sample_data,
        tmp_path,
    )

    assert summary["status"] == "PASS"

    expected = [
        "business_rules.csv",
        "business_summary.json",
        "business_report.html",
    ]

    for filename in expected:
        assert (
            tmp_path / filename
        ).is_file()

    saved = json.loads(
        (
            tmp_path / "business_summary.json"
        ).read_text(encoding="utf-8")
    )

    assert saved["rules_evaluated"] == 9

    report = (
        tmp_path / "business_report.html"
    ).read_text(encoding="utf-8")

    assert "RIDE360" in report
    assert "BR001" in report
