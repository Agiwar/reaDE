"""Connection interface protocol for health checking."""

from types import TracebackType
from typing import Protocol


class ConnectionInterface(Protocol):
    """Protocol for connection lifecycle and health checking.

    This interface is generic and can be implemented by database connectors,
    message queue clients (Kafka, RabbitMQ), cache clients (Redis), etc.
    """

    def __enter__(self) -> "ConnectionInterface":
        """Enter the runtime context.

        Returns:
            The connection interface instance.
        """
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Exit the runtime context.

        Args:
            exc_type: The exception type.
            exc_value: The exception value.
            traceback: The traceback object.
        """
        ...

    def connect(self) -> None:
        """Establish the connection."""
        ...

    def close(self) -> None:
        """Close the connection."""
        ...

    def is_connected(self) -> bool:
        """Check if the connection is active.

        Returns:
            True if connected, False otherwise.
        """
        ...
