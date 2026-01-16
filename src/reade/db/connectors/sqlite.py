"""SQLite database connector."""

import sqlite3

from reade.config.models import SqliteCredentials
from reade.core.base.connector import ConnectionBase


class SqliteConnector(ConnectionBase[sqlite3.Connection]):
    """SQLite database connector.

    Provides connection management and health checking for SQLite databases.
    Uses Python's built-in sqlite3 module.

    Args:
        credentials: SQLite credentials containing the database path.

    Example:
        >>> from reade.config.models import SqliteCredentials
        >>> credentials = SqliteCredentials(database="/path/to/db.sqlite")
        >>> with SqliteConnector(credentials) as conn:
        ...     print(conn.is_connected())
        True
    """

    def __init__(self, credentials: SqliteCredentials) -> None:
        """Initialize the SQLite connector.

        Args:
            credentials: SQLite credentials with database path.
        """
        super().__init__()
        self._credentials = credentials

    def connect(self) -> None:
        """Establish connection to SQLite database.

        Creates the database file if it doesn't exist.
        Use `:memory:` for an in-memory database.
        """
        self._connection = sqlite3.connect(self._credentials.database)

    def close(self) -> None:
        """Close the SQLite connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def is_connected(self) -> bool:
        """Check if connection is active.

        Returns:
            True if connection exists, False otherwise.
        """
        return self._connection is not None

    def ping(self) -> bool:
        """Perform health check by executing a simple query.

        Returns:
            True if connection is healthy, False otherwise.
        """
        if self._connection is None:
            return False

        try:
            self._connection.execute("SELECT 1")
        except sqlite3.Error:
            return False
        else:
            return True
