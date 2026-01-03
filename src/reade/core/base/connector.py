"""Base connection with shared logic."""

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Any


class ConnectionBase(ABC):
    """Base class for connection.

    Provides common lifecycle management for connections.
    Subclasses must implement connect(), close(), is_connected(), and ping().
    """

    def __init__(self) -> None:
        """Initialize the connection."""
        self._connection: Any = None

    def __enter__(self) -> "ConnectionBase":
        """Enter the runtime context.

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
        """Exit the runtime context and close the connection.

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
        """Close the connection."""
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if the connection is active.

        Returns:
            True if connected, False otherwise.
        """
        ...

    @abstractmethod
    def ping(self) -> bool:
        """Perform an active health check on the connection.

        Unlike is_connected() which may only check local state,
        ping() should perform a round-trip check (e.g., SELECT 1 for DBs).

        Returns:
            True if the connection is healthy, False otherwise.
        """
        ...

    @property
    def connection(self) -> Any:
        """Get the underlying connection.

        Returns:
            The underlying driver connection (e.g., psycopg2.Connection).

        Raises:
            ValueError: If the connection is not initialized.
        """
        if self._connection is None:
            raise ValueError("Connection is not initialized.")

        return self._connection
