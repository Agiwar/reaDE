"""Base connection with shared lifecycle logic."""

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Any, Self

from reade.core.errors.db import NotConnectedError


class ConnectionBase[T](ABC):
    """Base class for database connectors.

    Provides context-manager lifecycle and guarded access to the
    underlying driver connection. Satisfies the ``ConnectionInterface``
    protocol.

    Type Parameters:
        T: The underlying driver connection type
            (e.g., ``sqlite3.Connection``).
    """

    def __init__(self) -> None:
        """Initialize an unconnected connector."""
        self._connection: T | None = None

    def __enter__(self) -> Self:
        """Enter the runtime context, establishing the connection.

        Entering the context is equivalent to calling connect().

        Returns:
            The connector instance.
        """
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Exit the runtime context, closing the connection.

        Equivalent to calling close(), including its no-op guarantee.

        Args:
            exc_type: The exception type.
            exc_value: The exception value.
            traceback: The traceback object.
        """
        self.close()

    @abstractmethod
    def connect(self) -> None:
        """Establish the connection."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Close the connection.

        Closing an unconnected or already-closed connection is a no-op.
        """
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if the connection is active.

        Only consults local state; it cannot detect server-side timeouts
        or half-open connections. Use ping() for an end-to-end check.

        Returns:
            True if connected, False otherwise.
        """
        ...

    @abstractmethod
    def ping(self) -> bool:
        """Perform an active, round-trip health check on the connection.

        Unlike is_connected(), which may only check local state, ping()
        must verify the peer end-to-end (e.g., ``SELECT 1`` for databases).

        Returns:
            True if the connection is healthy, False otherwise.
        """
        ...

    @abstractmethod
    def execute(self, sql: str) -> list[tuple[Any, ...]]:
        """Execute a SQL statement and return all result rows, materialized.

        Statements without a result set (DDL, INSERT) return an empty
        list. Driver specifics — cursors, fetch styles — are the
        implementation's concern and never leak to callers.

        Args:
            sql: The SQL statement to execute.

        Returns:
            All result rows as tuples.

        Raises:
            NotConnectedError: If connect() has not established a
                connection.
            DbError: If the driver fails to execute the statement or
                fetch its results. The driver exception is attached as
                the cause.
        """
        ...

    @property
    def connection(self) -> T:
        """The underlying driver connection.

        Returns:
            The driver connection (e.g., ``sqlite3.Connection``).

        Raises:
            NotConnectedError: If connect() has not established a
                connection.
        """
        if self._connection is None:
            raise NotConnectedError("Connection is not established; call connect().")
        return self._connection
