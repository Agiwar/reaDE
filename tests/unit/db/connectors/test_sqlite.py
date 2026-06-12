"""Tests for SqliteConnector specifics beyond the ConnectionInterface contract."""

from pathlib import Path

import pytest

from reade.core.errors import DbError
from reade.db import SqliteConnector


class TestSqliteConnector:
    def test_connect_creates_database_file(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"

        with SqliteConnector(database=str(db_path)):
            assert db_path.exists()

    def test_connect_when_connected_is_noop(self) -> None:
        connector = SqliteConnector(database=":memory:")
        connector.connect()
        first = connector.connection

        connector.connect()

        assert connector.connection is first
        connector.close()

    def test_connect_failure_raises_db_error_with_cause(self, tmp_path: Path) -> None:
        connector = SqliteConnector(database=str(tmp_path / "no_such_dir" / "x.db"))

        with pytest.raises(DbError) as exc_info:
            connector.connect()

        assert exc_info.value.__cause__ is not None

    def test_ping_true_when_healthy(self) -> None:
        with SqliteConnector(database=":memory:") as connector:
            assert connector.ping()

    def test_connection_exposes_driver_connection(self) -> None:
        with SqliteConnector(database=":memory:") as connector:
            cursor = connector.connection.execute("SELECT 1")

            assert cursor.fetchone() == (1,)
