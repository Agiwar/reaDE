"""Tests for SqliteConnector."""

from pathlib import Path

import pytest

from reade.config.models import SqliteCredentials
from reade.db.connectors import SqliteConnector


class TestSqliteConnector:
    """Tests for SqliteConnector."""

    def test_connect_creates_file(self, tmp_path: Path) -> None:
        """Connect creates database file if it doesn't exist."""
        db_path = tmp_path / "test.db"
        creds = SqliteCredentials(database=str(db_path))

        connector = SqliteConnector(creds)
        connector.connect()

        assert db_path.exists()
        connector.close()

    def test_connect_memory_database(self) -> None:
        """Connect works with in-memory database."""
        creds = SqliteCredentials(database=":memory:")

        connector = SqliteConnector(creds)
        connector.connect()

        assert connector.is_connected()
        connector.close()

    def test_close_sets_connection_to_none(self, tmp_path: Path) -> None:
        """Close sets connection to None."""
        db_path = tmp_path / "test.db"
        creds = SqliteCredentials(database=str(db_path))

        connector = SqliteConnector(creds)
        connector.connect()
        connector.close()

        assert not connector.is_connected()

    def test_is_connected_false_before_connect(self) -> None:
        """is_connected returns False before connect is called."""
        creds = SqliteCredentials(database=":memory:")
        connector = SqliteConnector(creds)

        assert not connector.is_connected()

    def test_is_connected_true_after_connect(self) -> None:
        """is_connected returns True after connect."""
        creds = SqliteCredentials(database=":memory:")

        connector = SqliteConnector(creds)
        connector.connect()

        assert connector.is_connected()
        connector.close()

    def test_ping_returns_true_when_healthy(self) -> None:
        """ping returns True when connection is healthy."""
        creds = SqliteCredentials(database=":memory:")

        connector = SqliteConnector(creds)
        connector.connect()

        assert connector.ping()
        connector.close()

    def test_ping_returns_false_when_not_connected(self) -> None:
        """ping returns False when not connected."""
        creds = SqliteCredentials(database=":memory:")
        connector = SqliteConnector(creds)

        assert not connector.ping()

    def test_context_manager_connects_and_closes(self) -> None:
        """Context manager connects on enter and closes on exit."""
        creds = SqliteCredentials(database=":memory:")

        with SqliteConnector(creds) as connector:
            assert connector.is_connected()
            assert connector.ping()

        assert not connector.is_connected()

    def test_connection_property_returns_underlying_connection(self) -> None:
        """connection property returns the sqlite3.Connection."""
        creds = SqliteCredentials(database=":memory:")

        with SqliteConnector(creds) as connector:
            conn = connector.connection
            cursor = conn.execute("SELECT 1")
            assert cursor.fetchone() == (1,)

    def test_connection_property_raises_when_not_connected(self) -> None:
        """connection property raises ValueError when not connected."""
        creds = SqliteCredentials(database=":memory:")
        connector = SqliteConnector(creds)

        with pytest.raises(ValueError, match="not initialized"):
            _ = connector.connection
