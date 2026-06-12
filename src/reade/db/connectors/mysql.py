"""MySQL database connector."""

from typing import TYPE_CHECKING, Any

from reade.core.base.connector import ConnectionBase
from reade.core.errors.db import DbError

if TYPE_CHECKING:
    import pymysql
else:
    try:
        import pymysql
    except ModuleNotFoundError:  # driver ships as the 'mysql' extra
        pymysql = None


class MysqlConnector(ConnectionBase["pymysql.connections.Connection[Any]"]):
    """MySQL/MariaDB connector built on the ``pymysql`` driver.

    Requires the ``mysql`` extra (``pip install 'reade[mysql]'``);
    constructing the connector without it raises ``ImportError``.

    Connections are opened in autocommit mode: each ``execute()`` statement
    is atomic and immediately durable — pymysql defaults autocommit off,
    and without it writes through the seam would vanish at ``close()``.
    Callers needing transactional control can manage it through the
    ``connection`` property.

    Example:
        >>> with MysqlConnector(
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
        port: int = 3306,
    ) -> None:
        """Initialize the connector.

        Args:
            host: Server hostname or IP address.
            database: Name of the database to connect to.
            user: Login user name.
            password: Login password.
            port: Server port. Defaults to MySQL's standard 3306.

        Raises:
            ImportError: If the ``pymysql`` driver is not installed
                (install the ``mysql`` extra).
        """
        super().__init__()
        if pymysql is None:
            raise ImportError(
                "MySQL support requires the 'mysql' extra: pip install 'reade[mysql]'"
            )
        self._host = host
        self._database = database
        self._user = user
        self._password = password
        self._port = port

    def connect(self) -> None:
        """Establish the connection.

        Connecting an already-connected connector is a no-op.

        Raises:
            DbError: If the server cannot be reached or rejects the
                connection.
        """
        if self._connection is not None:
            return
        try:
            self._connection = pymysql.connect(
                host=self._host,
                port=self._port,
                database=self._database,
                user=self._user,
                password=self._password,
                autocommit=True,
            )
        except pymysql.MySQLError as e:
            raise DbError(
                f"Failed to connect to MySQL database {self._database!r} "
                f"at {self._host}:{self._port}"
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
        except pymysql.MySQLError as e:
            raise DbError("Failed to close MySQL connection") from e
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
                # description is the no-result-set signal across drivers;
                # gate on it rather than trusting fetch semantics.
                if cursor.description is None:
                    return []
                rows = cursor.fetchall()
        except pymysql.MySQLError as e:
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
            with self._connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except pymysql.MySQLError:
            return False
        return True
