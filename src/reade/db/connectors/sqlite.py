"""SQLite database connector."""

import sqlite3
from typing import Any

from reade.core.base.connector import ConnectionBase
from reade.core.errors.db import DbError


class SqliteConnector(ConnectionBase[sqlite3.Connection]):
    """SQLite connector built on the stdlib ``sqlite3`` module.

    Zero-setup backend: connecting creates the database file if it does
    not exist; use ``:memory:`` for an in-memory database.

    Example:
        >>> with SqliteConnector(database=":memory:") as connector:
        ...     connector.ping()
        True
    """

    def __init__(self, database: str) -> None:
        """Initialize the connector.

        Args:
            database: Path to the SQLite database file, or ``:memory:``.
        """
        super().__init__()
        self._database = database

    def connect(self) -> None:
        """Establish the connection.

        Connecting an already-connected connector is a no-op.

        Raises:
            DbError: If the database cannot be opened.
        """
        if self._connection is not None:
            return
        try:
            self._connection = sqlite3.connect(self._database)
        except sqlite3.Error as e:
            raise DbError(
                f"Failed to connect to SQLite database {self._database!r}"
            ) from e

    def close(self) -> None:
        """Close the connection.

        Closing an unconnected or already-closed connection is a no-op.

        Raises:
            DbError: If the driver fails to close the connection.
        """
        if self._connection is None:
            return
        try:
            self._connection.close()
        except sqlite3.Error as e:
            raise DbError("Failed to close SQLite connection") from e
        self._connection = None

    def is_connected(self) -> bool:
        """Check if the connection is active.

        Only consults local state; use ping() for an end-to-end check.

        Returns:
            True if connected, False otherwise.
        """
        return self._connection is not None

    def execute(self, sql: str) -> list[tuple[Any, ...]]:
        """Execute a SQL statement and return all result rows, materialized.

        Statements without a result set (DDL, INSERT) return an empty
        list.

        Args:
            sql: The SQL statement to execute.

        Returns:
            All result rows as tuples.

        Raises:
            NotConnectedError: If the connector is not connected.
            DbError: If the driver fails to execute the statement or
                fetch its results.
        """
        try:
            cursor = self.connection.execute(sql)
            rows = cursor.fetchall()
        except sqlite3.Error as e:
            raise DbError("Failed to execute SQL statement") from e
        return [tuple(row) for row in rows]

    def ping(self) -> bool:
        """Perform a round-trip health check (``SELECT 1``).

        Returns:
            True if the connection is healthy, False if unconnected or
            the round trip fails.
        """
        if self._connection is None:
            return False
        try:
            self._connection.execute("SELECT 1")
        except sqlite3.Error:
            return False
        return True
