"""Tests for SqliteConnector."""

from pathlib import Path

import pytest

from reade.config.models import SqliteCredentials
from reade.db.connectors import SqliteConnector


@pytest.fixture
def memory_creds() -> SqliteCredentials:
    """In-memory SQLite credentials."""
    return SqliteCredentials(database=":memory:")


class TestSqliteConnector:
    """Tests for SqliteConnector."""

    def test_connect_creates_file(self, tmp_path: Path) -> None:
        """Connect creates database file if it doesn't exist."""
        db_path = tmp_path / "test.db"
        creds = SqliteCredentials(database=str(db_path))

        with SqliteConnector(creds):
            assert db_path.exists()

    def test_connect_memory_database(self, memory_creds: SqliteCredentials) -> None:
        """Connect works with in-memory database."""
        with SqliteConnector(memory_creds) as connector:
            assert connector.is_connected()

    def test_close_sets_connection_to_none(self, tmp_path: Path) -> None:
        """Close sets connection to None."""
        db_path = tmp_path / "test.db"
        creds = SqliteCredentials(database=str(db_path))

        connector = SqliteConnector(creds)
        connector.connect()
        connector.close()

        assert not connector.is_connected()

    def test_is_connected_false_before_connect(
        self,
        memory_creds: SqliteCredentials,
    ) -> None:
        """is_connected returns False before connect is called."""
        connector = SqliteConnector(memory_creds)
        assert not connector.is_connected()

    def test_is_connected_true_after_connect(
        self,
        memory_creds: SqliteCredentials,
    ) -> None:
        """is_connected returns True after connect."""
        with SqliteConnector(memory_creds) as connector:
            assert connector.is_connected()

    def test_ping_returns_true_when_healthy(
        self,
        memory_creds: SqliteCredentials,
    ) -> None:
        """ping returns True when connection is healthy."""
        with SqliteConnector(memory_creds) as connector:
            assert connector.ping()

    def test_ping_returns_false_when_not_connected(
        self,
        memory_creds: SqliteCredentials,
    ) -> None:
        """ping returns False when not connected."""
        connector = SqliteConnector(memory_creds)
        assert not connector.ping()

    def test_context_manager_connects_and_closes(
        self,
        memory_creds: SqliteCredentials,
    ) -> None:
        """Context manager connects on enter and closes on exit."""
        with SqliteConnector(memory_creds) as connector:
            assert connector.is_connected()
            assert connector.ping()

        assert not connector.is_connected()

    def test_connection_property_returns_underlying_connection(
        self,
        memory_creds: SqliteCredentials,
    ) -> None:
        """connection property returns the sqlite3.Connection."""
        with SqliteConnector(memory_creds) as connector:
            cursor = connector.connection.execute("SELECT 1")
            assert cursor.fetchone() == (1,)

    def test_connection_property_raises_when_not_connected(
        self,
        memory_creds: SqliteCredentials,
    ) -> None:
        """connection property raises ValueError when not connected."""
        connector = SqliteConnector(memory_creds)

        with pytest.raises(ValueError, match="not initialized"):
            _ = connector.connection
