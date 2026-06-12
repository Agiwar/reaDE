"""PostgreSQL database connector."""

from typing import TYPE_CHECKING, Any

from reade.core.base.connector import ConnectionBase
from reade.core.errors.db import DbError
from reade.db._retry import connect_with_retry

if TYPE_CHECKING:
    import psycopg
else:
    try:
        import psycopg
    except ModuleNotFoundError:  # driver ships as the 'postgres' extra
        psycopg = None


class PostgresConnector(ConnectionBase["psycopg.Connection[tuple[Any, ...]]"]):
    """PostgreSQL connector built on the ``psycopg`` (v3) driver.

    Requires the ``postgres`` extra (``pip install 'reade[postgres]'``);
    constructing the connector without it raises ``ImportError``.

    Connections are opened in autocommit mode: each ``execute()`` statement
    is independent, so a failed statement never leaves the connection in a
    failed-transaction state that would poison subsequent statements or
    health checks. Callers needing transactional control can manage it
    through the ``connection`` property.

    Transient connect failures can be retried (``connect_attempts`` /
    ``retry_backoff``); ``execute()`` and ``ping()`` are never retried.

    Example:
        >>> with PostgresConnector(
        ...     host="localhost", database="app", user="app", password="..."
        ... ) as connector:
        ...     connector.ping()
        True
    """

    def __init__(
        self,
        host: str,
        database: str,
        user: str,
        password: str,
        port: int = 5432,
        connect_timeout: int | None = None,
        connect_attempts: int = 1,
        retry_backoff: float = 0.5,
    ) -> None:
        """Initialize the connector.

        Args:
            host: Server hostname or IP address.
            database: Name of the database to connect to.
            user: Login role name.
            password: Login password.
            port: Server port. Defaults to PostgreSQL's standard 5432.
            connect_timeout: Per-attempt connection timeout in seconds.
                ``None`` keeps the driver default — libpq waits
                indefinitely, so bounded retry *time* (not just bounded
                attempts) requires setting this.
            connect_attempts: Total connect() attempts; 1 (the default)
                means no retry.
            retry_backoff: Delay before the second attempt, in seconds;
                doubles after each subsequent failure.

        Raises:
            ImportError: If the ``psycopg`` driver is not installed
                (install the ``postgres`` extra).
            ValueError: If ``connect_attempts`` is less than 1.
        """
        super().__init__()
        if psycopg is None:
            raise ImportError(
                "PostgreSQL support requires the 'postgres' extra: "
                "pip install 'reade[postgres]'"
            )
        if connect_attempts < 1:
            raise ValueError(f"connect_attempts must be >= 1, got {connect_attempts}")
        self._host = host
        self._database = database
        self._user = user
        self._password = password
        self._port = port
        self._connect_timeout = connect_timeout
        self._connect_attempts = connect_attempts
        self._retry_backoff = retry_backoff

    def connect(self) -> None:
        """Establish the connection, retrying transient failures.

        Connecting an already-connected connector is a no-op. Failed
        attempts are retried up to ``connect_attempts`` with doubling
        backoff; only connection establishment is retried, never
        statement execution.

        Raises:
            DbError: If the server cannot be reached or rejects the
                connection on the final attempt.
        """
        if self._connection is not None:
            return
        try:
            self._connection = connect_with_retry(
                self._open,
                attempts=self._connect_attempts,
                backoff=self._retry_backoff,
                retry_on=(psycopg.Error,),
            )
        except psycopg.Error as e:
            raise DbError(
                f"Failed to connect to PostgreSQL database {self._database!r} "
                f"at {self._host}:{self._port}"
            ) from e

    def _open(self) -> "psycopg.Connection[tuple[Any, ...]]":
        """Open one driver connection (a single attempt, no mapping)."""
        kwargs: dict[str, Any] = {
            "host": self._host,
            "port": self._port,
            "dbname": self._database,
            "user": self._user,
            "password": self._password,
            "autocommit": True,
        }
        if self._connect_timeout is not None:
            kwargs["connect_timeout"] = self._connect_timeout
        return psycopg.connect(**kwargs)

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
        except psycopg.Error as e:
            raise DbError("Failed to close PostgreSQL connection") from e
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
            with self.connection.cursor() as cursor:
                cursor.execute(sql)
                # Fetching after a statement with no result set raises in
                # psycopg (unlike sqlite3); description is the seam-safe
                # signal that rows exist.
                if cursor.description is None:
                    return []
                rows = cursor.fetchall()
        except psycopg.Error as e:
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
        except psycopg.Error:
            return False
        return True
