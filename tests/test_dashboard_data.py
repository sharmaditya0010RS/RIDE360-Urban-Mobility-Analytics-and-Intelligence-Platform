
"""Tests for the RIDE360 dashboard data access layer."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from psycopg import sql

from ride360.dashboard_data import (
    ALLOWED_VIEWS,
    fetch_dataframe,
    fetch_view,
    get_connection_config,
    get_view_name,
    to_csv_bytes,
)


def test_allowed_views_are_qualified():
    assert ALLOWED_VIEWS
    assert all(
        name.startswith(
            ("ride360_analytics.", "ride360_audit.")
        )
        for name in ALLOWED_VIEWS.values()
    )


def test_unknown_view_is_rejected():
    with pytest.raises(ValueError, match="Unsupported"):
        fetch_view("ride360_raw.booking_records", 1)


@pytest.mark.parametrize("batch_id", [0, -1, "1", None])
def test_invalid_batch_id_is_rejected(batch_id):
    with pytest.raises(ValueError, match="positive integer"):
        fetch_view("executive", batch_id)


def test_missing_env_file():
    with pytest.raises(FileNotFoundError):
        get_connection_config(
            Path("this_file_does_not_exist.env")
        )


def test_database_config_from_env(tmp_path):
    env_file = tmp_path / ".env"

    env_file.write_text(
        "DB_HOST=localhost\n"
        "DB_PORT=5433\n"
        "DB_NAME=ride360_test\n"
        "DB_USER=test_user\n"
        "DB_PASSWORD=test_password\n",
        encoding="utf-8",
    )

    config = get_connection_config(env_file)

    assert config["host"] == "localhost"
    assert config["port"] == 5433
    assert config["dbname"] == "ride360_test"
    assert config["user"] == "test_user"
    assert config["password"] == "test_password"


def test_missing_database_credentials(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DB_HOST=localhost\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Missing PostgreSQL"):
        get_connection_config(env_file)


def test_csv_export():
    frame = pd.DataFrame(
        {
            "vehicle": ["Auto", "Bike"],
            "bookings": [100, 200],
        }
    )

    result = to_csv_bytes(frame)

    assert isinstance(result, bytes)
    assert b"vehicle,bookings" in result
    assert b"Auto,100" in result
    assert b"Bike,200" in result


def test_empty_csv_export():
    frame = pd.DataFrame(
        columns=["batch_id", "total_bookings"]
    )

    result = to_csv_bytes(frame)

    assert b"batch_id,total_bookings" in result


def test_fetch_dataframe_uses_read_only_connection():
    cursor = MagicMock()
    cursor.fetchall.return_value = [
        {"batch_id": 1, "total_bookings": 150000}
    ]

    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.cursor.return_value.__enter__.return_value = cursor

    with patch(
        "ride360.dashboard_data.psycopg.connect",
        return_value=connection,
    ) as connect_mock:
        result = fetch_dataframe(
            "SELECT * FROM test WHERE batch_id = %s",
            (1,),
            config={
                "host": "localhost",
                "dbname": "test",
                "user": "test",
                "password": "test",
            },
        )

    assert len(result) == 1
    assert result.iloc[0]["total_bookings"] == 150000

    cursor.execute.assert_called_once()

    actual_query, actual_params = cursor.execute.call_args.args

    assert isinstance(actual_query, sql.SQL)
    assert actual_query.as_string() == (
        "SELECT * FROM test WHERE batch_id = %s"
    )
    assert actual_params == (1,)

    assert (
        connect_mock.call_args.kwargs["options"]
        == "-c default_transaction_read_only=on"
    )


def test_fetch_view_uses_parameterized_batch():

    expected = pd.DataFrame(
        [{"batch_id": 1, "total_booking_records": 150000}]
    )

    with patch(
        "ride360.dashboard_data.fetch_dataframe",
        return_value=expected,
    ) as fetch_mock:
        result = fetch_view("executive", 1)

    assert len(result) == 1


    args, _ = fetch_mock.call_args

    assert get_view_name("executive") in args[0]
    assert "WHERE batch_id = %s" in args[0]
    assert args[1] == (1,)
